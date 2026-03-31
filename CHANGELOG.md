Keep a Changelog 準拠 — CHANGELOG.md
※コード内容から推測して作成しています。実際の変更履歴と差異がある可能性があります。

# Changelog

すべての注記は SemVer に従います。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-03-31

初回リリース — KabuSys: 日本株自動売買システム（プロトタイプ／研究用）

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring（将来的モジュール構成の骨子）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索して自動ロード。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサーは以下をサポート:
    - コメント行、先頭の export キーワード、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォートあり/なしの挙動差）。
  - Settings クラスを追加（settings = Settings() で利用可能）。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視設定 / システム設定（env, log_level）などのプロパティを提供。
    - デフォルト値を設定（例: KABUSYS duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db、PID ファイル: data/execution.pid）。
    - 有効値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - 必須環境変数取得時は未設定で ValueError を送出するヘルパーを用意。

- AI（自然言語処理）関連モジュールを追加（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用い、OpenAI（gpt-4o-mini）でニュースごとのセンチメントを算出し ai_scores テーブルへ書き込むワークフローを実装。
    - 時間ウィンドウ計算（JST ベース → UTC へ変換）、記事集約（銘柄ごとに最新 N 件・文字数トリム）、バッチ（最大 20 銘柄）での API 呼び出し、応答バリデーション、スコアクリップ ±1.0。
    - レート制限・ネットワーク・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - DuckDB 互換性のため executemany の空リスト回避等の実装（部分失敗時に既存スコアを保護する DELETE → INSERT 戦略）。
    - テスト用に内部の _call_openai_api をモック可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を決定し market_regime に書き込む。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI での JSON 応答パース、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功 1 を返す（OpenAI API キー未設定時は ValueError）。

- リサーチ（研究）モジュールを追加（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - ファクター計算: モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR）、バリュー（PER、ROE）等を DuckDB 上の SQL で実装。
    - 各関数は target_date を受け取り、(date, code) ベースの dict リストを返す。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数、ファクター統計サマリ（factor_summary）等を実装（外部ライブラリに依存しない実装）。
  - research パッケージは便利関数を再エクスポート（zscore_normalize 等）。

- データ管理モジュールを追加（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=...) を実装（J-Quants から取得 → jq.save_market_calendar で保存）。
    - 安全対策: 最大探索日数、バックフィル、健全性チェック（将来日付異常の検知）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラー概要などを保持）。
    - 差分フェッチ、保存、品質チェックのフロー設計（jq クライアント、quality モジュール経由）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - data.etl は ETLResult を再エクスポート。

- その他の実装上の配慮
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() をスコアリング関数内部で直接参照しない設計（target_date パラメータ駆動）。
  - DuckDB の互換性や欠陥（executemany の空リスト）に対する回避処理を実装。
  - OpenAI 呼び出し時は JSON Mode を利用し、厳密な JSON 応答を期待するプロンプト設計。
  - ロギング（logger）を各モジュールで活用し、処理状況・警告・例外を記録。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- OpenAI 連携の堅牢化
  - レート制限、ネットワーク切断、タイムアウト、5xx に対する再試行・バックオフを実装。
  - API レスポンスの JSON パース失敗時は例外を伝播させずフェイルセーフ（0.0 またはスキップ）する挙動を追加してワークフローの堅牢性を向上。
- DB 書き込みの冪等性・トランザクション処理を実装（BEGIN/COMMIT/ROLLBACK ハンドリング）。ROLLBACK 実行失敗時は警告ログ出力。

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 必須の環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- 環境変数の取り扱い: OS 環境を保護する protected list により .env による上書きを制御。

### 注意事項 / 既知の問題 (Notes / Known issues)
- OPENAI_API_KEY 未設定時
  - AI 関連の公開 API（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を投げます。
- DuckDB 互換性
  - executemany に空リストを渡せない制約を回避するコードが入っています（空チェックを行ってから executemany）。
- テスト支援
  - news_nlp / regime_detector 内の _call_openai_api は unittest.mock.patch で差し替え可能に実装済み。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 実装上の未完・切断箇所
  - src/kabusys/data/pipeline.py の末尾付近に _get_max_date の返却処理が不完全な形で切れている（コード断片が残っている）。実行環境によっては該当箇所が原因で例外となる可能性があるため確認が必要。
- 出力・保存ポリシー
  - AI 応答は厳密な JSON を期待するが、LLM の不確実性に備えてパース回復ロジックを入れている（最外側の {} を抽出する等）。
- ローカルデフォルトパス
  - DuckDB/SQLite のデフォルトパスはプロジェクト内 data/ 以下に設定されているため、運用時は適切な永続ストレージパスを環境変数で上書き推奨。

--- 
今後の改善提案（コードベースからの推測）
- pipeline モジュールの未完成部分修正とユニットテスト追加。
- OpenAI 呼び出しのメトリクス収集（成功率・レイテンシ等）と監視アラート連携。
- strategy / execution / monitoring の具体実装（現状はパッケージ構成のプレースホルダ）。
- E2E テスト用の Docker / CI 設定（DuckDB を利用したテストセットアップ、API キーのモック化）。

以上。必要なら各セクションをさらに詳細化（関数単位の変更ログ、ファイル毎の差分想定など）して作成できます。どの粒度で記載するか指示ください。