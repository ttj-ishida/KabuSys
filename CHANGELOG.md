# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベース（kabusys パッケージ）から推測できる実装・仕様を基に作成した想定の変更履歴です。

注意: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース日や詳細はリポジトリの履歴に合わせて調整してください。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28

### Added
- 初回リリース: `kabusys` パッケージの公開。
  - パッケージトップでのバージョン管理: `__version__ = "0.1.0"`。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ として公開。

- 環境設定/ロード機能
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定を取得するプロパティ群（J-Quants トークン、kabuAPI パスワード、KABU API の base URL、Slack トークン/チャンネル、DB パス、環境/ログレベル判定など）。
  - 自動 .env ロード機能を実装:
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して検出。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数を保護する機能（既存の環境変数を protected として上書きしない）。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーの実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、コメント処理に対応）。
  - 環境値検証（`KABUSYS_ENV` は `development|paper_trading|live`、`LOG_LEVEL` は標準ログレベルの検証）。

- データプラットフォーム関連（DuckDB ベース）
  - `kabusys.data.pipeline.ETLResult` データクラスを追加（ETL 実行結果、品質チェック結果、エラー一覧などを保持）。`kabusys.data.etl` で再エクスポート。
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理、営業日判定ユーティリティを実装: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`。
    - カレンダーの夜間更新ジョブ `calendar_update_job`（J-Quants クライアント経由で差分取得・バックフィル・健全性チェック・冪等保存を行う）。
    - カレンダー未取得時の曜日ベースのフォールバック実装（週末は非営業日扱い）。
    - 最大探索日数やバックフィル日数等の安全パラメータを導入。

- 研究（Research）機能
  - `kabusys.research` パッケージを追加 / 公開:
    - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`（`kabusys.research.factor_research`）。
    - 特徴量/評価ユーティリティ: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（`kabusys.research.feature_exploration`）。
    - `zscore_normalize` を `kabusys.data.stats` から再エクスポート。
  - すべて DuckDB 接続を受け取り SQL + Python の組合せで実装。外部ライブラリに依存しない設計。

- AI（LLM）関連機能
  - `kabusys.ai.news_nlp`:
    - ニュース記事から銘柄ごとのセンチメントスコアを算出し、`ai_scores` テーブルへ書き込む `score_news` 関数を実装。
    - ニュース収集ウィンドウの計算 (`calc_news_window`)（JST の前日 15:00 〜 当日 08:30 に対応し、内部は UTC naive datetime を使用）。
    - バッチ処理（1 API 呼び出しにつき最大 20 銘柄）・1 銘柄あたりの最大記事数/文字数トリムを実装。
    - OpenAI（`gpt-4o-mini`）への JSON モード呼び出しとレスポンス検証ロジック、失敗時のエクスポネンシャルバックオフリトライ（429、ネットワーク断、タイムアウト、5xx を対象）。
    - レスポンスパース時の頑健性強化（余分な前後テキストから最外の {} を抽出する復元処理等）。
    - DuckDB の executemany の制約に配慮した部分置換（DELETE → INSERT）処理により冪等性・部分失敗耐性を確保。
    - テスト容易性のために内部 OpenAI 呼び出し点を patch できる設計（`_call_openai_api` の差し替えが可能）。

  - `kabusys.ai.regime_detector`:
    - 日次の市場レジーム判定 `score_regime` を実装。ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して `market_regime` テーブルへ書き込む。
    - look-ahead バイアス防止のため、すべての処理が `target_date` を受け取り UTC/DB の日付範囲を閉区間/半開区間で扱う実装。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）、および JSON レスポンスの検証。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK。

- OpenAI クライアントとモデル
  - デフォルトモデル `gpt-4o-mini` を使用する旨を明記。
  - API キー注入は引数経由または `OPENAI_API_KEY` 環境変数から解決。未設定時は ValueError を発生させる。

- ロギングと運用上の安全対策
  - 各モジュールで詳細なログ出力（info/debug/warning/exception）を追加。
  - look-ahead バイアス防止設計: 全ての時系列解析関数は内部で datetime.today()/date.today() を直接参照せず、必ず `target_date` を引数として受ける。
  - DuckDB 互換性考慮（executemany の空リスト回避など）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- JSON レスポンスのパースと検証に関する耐障害性を強化（余分テキストの復元、型チェック、未知銘柄や非数値スコアの無視）。
- OpenAI 呼び出しでの 5xx / ネットワークエラー等に対するリトライ・バックオフを実装して冪等かつ安全に継続処理するように改善。

### Security
- .env 読み込み時に OS 環境変数を保護する実装（既存変数は上書きされない）。
- 機密情報（J-Quants トークン、Kabu API パスワード、Slack トークン等）は必須プロパティとして取得時に未設定なら明示的なエラーを発生させる設計。

### Removed
- （初回リリースにつき該当なし）

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 機能を利用する場合）
- オプション / デフォルト:
  - KABUSYS_ENV のデフォルトは `development`（有効値: development, paper_trading, live）。
  - LOG_LEVEL のデフォルトは `INFO`。
  - KABU_API_BASE_URL のデフォルトは `http://localhost:18080/kabusapi`。
  - DB ファイルパスのデフォルト: `DUCKDB_PATH = data/kabusys.duckdb`, `SQLITE_PATH = data/monitoring.db`。
- テスト／CI:
  - 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定。
  - OpenAI 呼び出し等は内部の `_call_openai_api` をモックすることでテスト可能。

---

（この CHANGELOG はソースコードの実装から推測して作成しています。実際のリリースノートとして使用する場合は、コミット履歴やリリース差分に基づき適宜修正してください。）