# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載しています。主にコードベースから推測して作成した初期リリース向けの変更履歴です。

全般的な方針：
- ルックアヘッドバイアス回避のため、datetime.today() / date.today() を直接参照しない実装方針を採用しています（分析 / AI / ETL すべてのモジュールで一貫）。
- DuckDB を主要な分析データベースとして使用。外部 API（J-Quants, OpenAI）との連携は明示的に注入可能・フェイルセーフ化しています。
- OpenAI 呼び出しはテスト差し替えが容易なように内部関数を設け、レスポンスの堅牢なバリデーションとリトライ戦略を備えています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-26
Added
- パッケージ初期リリース。
  - バージョン: 0.1.0
  - パッケージ説明: KabuSys - 日本株自動売買システム

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み実装（プロジェクトルート検出：.git / pyproject.toml を起点）。
  - .env パーサ実装（export 形式・シングル/ダブルクォート・エスケープ・インラインコメント処理対応）。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 環境変数の必須チェック関数 _require と Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パス等のプロパティを公開。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックと便利なブールプロパティ（is_live / is_paper / is_dev）。

- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を利用した営業日判定（is_trading_day, is_sq_day）。
    - 翌営業日・前営業日の探索（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）。
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ（calendar_update_job）。バックフィルや健全性チェックを搭載。
    - DB が未取得の場合の曜日ベースフォールバック（週末は非営業日扱い）。
  - ETL パイプライン（pipeline, etl）
    - ETL 結果格納用データクラス ETLResult の定義（品質チェック結果・エラー集約・辞書化ユーティリティ）。
    - 差分更新・最終取得日管理・バックフィルロジック・品質チェック統合のための下地実装。
    - ETLResult をエクスポートする薄いインターフェース（etl.py）。
  - jquants_client との統合ポイント（fetch/save を呼ぶ想定の実装場所を確保）。

- AI / NLP（kabusys.ai）
  - ニュース NLP（news_nlp）
    - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメントスコアリング。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に対応する UTC 範囲）。
    - 銘柄ごとに最新記事を集約し、1銘柄1スコアで評価。入力サイズ対策（最大記事数・文字数トリム）。
    - バッチ処理（最大20銘柄/リクエスト）・JSON mode レスポンス検証・結果のクリップ ±1.0。
    - レート制限・ネットワーク断・5xx に対する指数バックオフリトライ、APIエラー時は安全にスキップ。
    - DuckDB への冪等的な書き込み（該当 date/code の DELETE → INSERT）を実装。部分失敗時に既存データを保護する設計。
    - テスト容易性のため _call_openai_api の差し替えを想定。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用し、データ不足時は中立（ma_ratio=1.0）で続行。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出し LLM 評価（最大20件）。
    - OpenAI API 呼び出しに対する堅牢なリトライと、失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL ウィンドウ関数を活用した効率的な実装。データ不足時に None を返す扱い。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、引数検証）。
    - IC（Information Coefficient）計算（calc_ic：ランク相関 Spearman ρ）。
    - ランク変換ユーティリティ（rank：同順位は平均ランク）。
    - ファクター統計サマリー（factor_summary：count/mean/std/min/max/median）。

Changed
- 初期設計での堅牢性強化（各所共通）
  - DuckDB の executemany に対する互換性問題に配慮（空リストバインド回避）。
  - OpenAI の JSON mode でも余計な前後テキストが混在するケースを想定して JSON 抽出ロジックを追加。
  - API エラー分類（429/ネットワーク断/タイムアウト/5xx をリトライ、その他は安全にスキップ）を明確化。
  - レスポンスパース失敗・不正な値はログ出力のうえフェイルセーフ（例外を投げず既定値にフォールバック）とするポリシーに統一。

Fixed
- 仕様上の落とし穴に対する対応
  - .env パーサでのクォート内エスケープ処理やインラインコメント解釈の不整合を解消。
  - market_calendar が未取得または部分的にしか登録されていない場合でも next/prev/get_trading_days が一貫した結果を返すよう修正（DB 値優先・未登録は曜日フォールバック）。
  - AI モジュールでの部分的な API 失敗が他銘柄の結果を消してしまうことを防ぐため、DB 書き込み時にスコープを限定（対象コードのみ削除して再挿入）。

Security
- 環境変数の上書き制御を実装（.env ロード時、既存 OS 環境変数は保護。override フラグと protected set を利用）。
- 必須トークン（OpenAI, J-Quants refresh token, Slack token など）は明示的にチェックして未設定時に早期にエラーを返す。

Notes / Known limitations
- 外部依存：
  - J-Quants クライアント（jquants_client）および実際の API キーは別途用意する必要があります。
  - OpenAI API（gpt-4o-mini）呼び出しは実環境の API キーが必要。テスト時はモック可能。
- 一部ファイルは設計ドキュメントに基づいた実装のため、環境依存の挙動（DB スキーマ、外部 API のレスポンス形式）に依存します。
- calendar_update_job / ETL 周りは実行に際して J-Quants からのデータ取得ロジック（fetch/save）の実装が前提です。

--- 

この CHANGELOG はコード内の docstring、関数名、設計方針コメントから推測して作成しています。追加のリリース履歴や過去の変更を反映する場合は、該当コミットやリリースノートの情報を提供してください。