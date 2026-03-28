# CHANGELOG

このプロジェクトでは「Keep a Changelog」仕様に準拠して変更履歴を管理します。  
フォーマットの詳細: https://keepachangelog.com/ja/

全般:
- 本リリースはパッケージ初期公開相当のまとめです。各モジュールの主要機能・設計方針・注意点を記載しています。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージ公開用の __all__ と __version__ を定義。

- 環境変数 / 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - .env / .env.local のロード順序を実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）を許可。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（コメント、export キーワード、クォートとエスケープ処理に対応）。
  - Settings クラスを提供し、アプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定など）をプロパティ経由で取得。
  - 必須環境変数未設定時は明確なエラー（ValueError）を送出する `_require` を実装。
  - KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装（許容値チェック）。

- データ関連 (kabusys.data)
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合の曜日ベースのフォールバックと、DB 登録値優先の一貫した補完ロジックを採用。
    - calendar_update_job: J-Quants から差分取得して冪等に保存する夜間バッチジョブ（バックフィル・健全性チェック付き）。
  - pipeline / etl:
    - ETLResult データクラスを公開。ETL の各種カウント、品質チェック結果、エラー集約を保持。
    - ETL パイプラインの補助ユーティリティ（テーブル存在チェック・最大日付取得・トレーディング日調整など）を実装。
    - 差分取得・バックフィル・品質チェック方針を実装（詳細は doc 相当の docstring に明記）。
  - etl モジュールと pipeline の公開インターフェースを整理（ETLResult を再エクスポート）。

- AI / ニュース NLP (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ：前日 15:00 JST ～ 当日 08:30 JST に対応（UTC 変換で DB 比較）。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - OpenAI 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx を対象）を指数バックオフで実装。
    - レスポンス検証: JSON パース、"results" キー、コード整合性、数値性、有限性を検証。無効レスポンスはスキップ。
    - 書き込みは部分失敗を避けるため、スコア取得済みコードのみを DELETE → INSERT（冪等）で更新。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - regime_detector:
    - ETF 1321（225連動）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事フィルタはマクロキーワードリストに基づく（最大 20 記事）。
    - OpenAI 呼び出しは gpt-4o-mini、JSON レスポンスを期待。API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジーム判定のスコア合成・閾値設定を実装し、market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に _call_openai_api の差し替えが可能。

- Research（ファクター計算 / 特徴量探索） (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高変化率）を DuckDB 上で計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - データ不足時の扱い（None 返却）や、計算ウィンドウのバッファ設計（スキャン期間）を実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）、IC（calc_ic: スピアマンのランク相関）、ランク生成（rank）、統計サマリ（factor_summary）を実装。
    - pandas 等外部ライブラリ不使用で標準ライブラリのみで実装。
  - research パッケージ __init__ で主要関数を公開。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で注入する設計。キー管理は呼び出し側で行うこと。
- .env 自動読み込みはデフォルトで有効だが、テスト等で明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 注意事項
- OpenAI 連携
  - news_nlp / regime_detector は OpenAI の Chat Completions API（gpt-4o-mini）を利用する。API キー未指定の場合は ValueError を送出するため、実行環境で OPENAI_API_KEY を準備してください。
  - レスポンスの堅牢化（パース失敗や予期しない出力の復元ロジック）を実装しているが、LLM の応答変動による部分失敗は起こり得ます。失敗時は該当チャンクをスキップして他銘柄の処理を続行します。
- ルックアヘッドバイアス対策
  - AI・研究モジュールともに内部で datetime.today() / date.today() を直接参照せず、呼び出し時に与えられた target_date に基づいて処理する設計です。バッチ化やバックテスト時のバイアス回避に配慮しています。
- DuckDB 互換性
  - 一部実装（executemany の空リスト禁止等）は DuckDB の既知の制約に配慮しているため、使用する DuckDB のバージョンによっては挙動が異なる可能性があります（ドキュメント参照）。
- テスト容易性
  - OpenAI 呼び出し箇所はモジュール内のプライベート関数をモック可能に実装しています（unittest.mock.patch 等で差し替え推奨）。

### Known issues / TODO
- PBR・配当利回り等のバリューファクターは未実装（calc_value の注記参照）。
- calendar_update_job の J-Quants クライアント実装（fetch/save）は別モジュールに依存しており、API 側の変更が影響する可能性があります。
- AI レスポンスの堅牢化は入れているが、LLM の出力仕様変更時の追加対応が必要。

--- 

今後のリリースでは、以下を検討しています:
- 追加ファクター（PBR、配当利回り等）の実装、
- AI モデル選択の抽象化とロギング詳細化、
- ETL のスケジューラ統合と監視ダッシュボード連携。