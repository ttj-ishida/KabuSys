# Changelog

すべての重要な変更を記録するためのログです。  
このファイルは「Keep a Changelog」のフォーマットに従い、セマンティックバージョニングを使用します。

※ 本ログはソースコードの内容から機能追加・設計方針・修正点を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。以下の主要機能および設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機構（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パース実装（コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い）。
  - OS 環境変数を保護する protected 上書き制御（.env.local は override）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック用 _require と Settings クラスを提供。
  - Settings による各種プロパティを実装（J-Quants, kabu API, Slack, DB パス（DuckDB/SQLite）, 監視閾値, 環境/ログレベル判定、is_live/is_paper/is_dev）。

- データ取得・ETL（kabusys.data.pipeline / etl）
  - ETLResult データクラスを定義し、ETL 実行結果と品質問題・エラー情報を管理。
  - ETL の差分更新・バックフィル・品質チェックを想定したインターフェース骨格（jquants_client 経由の差分取得・保存を想定）。

- マーケットカレンダー（kabusys.data.calendar_management）
  - market_calendar を利用した営業日判定ロジック（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
  - DB データ優先、未登録日に対する曜日ベースのフォールバック。
  - calendar_update_job: J-Quants から差分取得して冪等保存する夜間バッチ機能。バックフィル・健全性チェック実装。
  - 最大探索日数やバックフィル日数などの安全ガード実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - score_news: raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_score）を ai_scores テーブルへ書き込み。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数上限（記事トリム）、チャンクごとのリトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）。
  - レスポンスの厳格なバリデーション（JSON 抽出、results キー検証、コード整合性、数値チェック、±1.0 クリッピング）。
  - DB への書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT の置換を行い冪等性を確保。
  - テスト容易性のため API 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。

- AI レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime に書き込み。
  - MA 計算は target_date 未満のデータのみ使用することでルックアヘッドバイアスを防止。
  - マクロ記事抽出はキーワードマッチング、LLM 呼び出しは JSON モードでスコアを取得、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
  - 冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック時の警告ログ。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を使用）。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率（データ不足時は None）。
    - Value: PER（EPS が 0/欠損なら None）、ROE（最新財務データを使用）。
  - feature_exploration: calc_forward_returns（任意ホライズン対応、ホライズン検証）、calc_ic（Spearman ランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）。
  - 外部依存を抑え、DuckDB + 標準ライブラリのみで実装。

- DuckDB / DB 安全対策
  - DuckDB を前提にした SQL 実装。
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約に配慮）。
  - BEGIN / COMMIT / ROLLBACK によるトランザクション制御とロールバック失敗時の警告。

- ロギングとエラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを追加（情報・警告・例外ログ）。
  - API レスポンスパース失敗や外部 API エラー時はフェイルセーフで処理を継続（例外を伝播させる箇所は DB 書き込み失敗など明示的に扱う）。

### Changed
- 初期リリースのため該当なし（新規実装）。

### Fixed
- .env パーサーでの細かなケースを考慮して実装（引用符内のエスケープ、インラインコメント扱い、export プレフィックス対応、空行・コメント行無視）。
- OpenAI API 呼び出しにおける 5xx とそれ以外の扱いを区別し、適切にリトライ判定・ログ出力。

### Security
- .env 読み込み時に OS 環境変数を保護する仕組み（既存 OS 環境変数を protected として上書き除外）。
- 設定値取得時に必須キーが未設定なら明示的に例外を投げる（_require）。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、内部実装は datetime.now()/date.today() を直接参照せず、外部から target_date を注入して計算を行う設計。
- 外部 API（OpenAI / J-Quants）失敗時はスコアに中立値を採用するなどフェイルセーフを導入し、ETL/スコア処理の堅牢性を高める方針。
- モジュール間の結合を低く保つため、内部の OpenAI 呼び出し関数は各モジュール固有に実装し、テスト時に差し替え可能とする。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に既存データを保護する設計。

---

今後のリリースでは、API クライアントの実装詳細、strategy / execution / monitoring モジュールの具体的な取引ロジックや実行フロー、テストカバレッジの明示、ドキュメント (StrategyModel.md / DataPlatform.md の補完) を追加していく予定です。