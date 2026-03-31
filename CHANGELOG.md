# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに準拠して記載します。  
このファイルはコードベースの現状（初期公開相当）から推測して生成しています。

## [Unreleased]
- （次回リリース用）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを公開します。主な機能群は設定管理、データETL・カレンダー管理、AIによるニュース分析／レジーム判定、リサーチ用のファクター計算および特徴量解析です。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を package root に定義（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 設定管理 (.env / 環境変数)
  - 自動 .env ロード機能を実装（プロジェクトルートの .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサは export 形式、シングル／ダブルクォートとバックスラッシュエスケープ、行内コメント処理に対応。
  - Settings クラスを提供（settings インスタンス）。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
    - KABU_API_BASE_URL のデフォルト (http://localhost:18080/kabusapi)。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 監視関係: PID_FILE_PATH, CPU/MEMORY/DISK の閾値（デフォルト値あり）。
    - 環境（KABUSYS_ENV）バリデーション: development / paper_trading / live。
    - ログレベル（LOG_LEVEL）バリデーション。

- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）へ送信。
    - JSON Mode による厳密な JSON レスポンス期待。response のバリデーションと数値クリップ（±1.0）。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1銘柄あたり記事数・文字数の上限でトークン肥大を制御。
    - リトライ（429、接続断、タイムアウト、5xx に対し指数バックオフ）。API 失敗時はフェイルセーフでスキップし、全体処理は継続。
    - 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
    - 公開 API: score_news(conn, target_date, api_key=None) -> 書き込み銘柄数。

  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を統合してレジーム（bull/neutral/bear）判定。
    - calc_news_window を使った過去ウィンドウ取得、_calc_ma200_ratio によるルックアヘッド排除。
    - OpenAI 呼び出しは独立実装。JSON レスポンスパース、リトライ、5xx の判定に対応。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化。
    - 公開 API: score_regime(conn, target_date, api_key=None) -> 1（成功を示す）。

- データモジュール (kabusys.data)
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラーリストなどを含む）。
    - 差分取得、バックフィル、品質検査フレームワークとの連携設計。
    - DuckDB 接続を前提とした実装。外部API呼び出し（J-Quants クライアント）は jquants_client 経由で抽象化。
    - kabusys.data.etl は ETLResult を再エクスポート。

  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - DB（market_calendar）に基づく判定を優先し、DB 未登録日は曜日ベースのフォールバック（週末＝非営業日）で一貫性を保つ設計。
    - calendar_update_job により J-Quants からの差分取得・冪等保存を行う（バックフィル・健全性チェックあり）。
    - 最大探索範囲やバックフィル日数、異常検知（将来日付の健全性チェック）を組み込み。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials のみ参照。
    - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - Volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）、ROE（最新財務データを結合）。
    - 計算は DuckDB 上のウィンドウ関数を利用して効率化。

  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。結合と None 除外、3 件未満で None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）・統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等外部依存なしで標準ライブラリと DuckDB を利用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは環境変数経由で扱う設計。Settings クラスが必須キーを検査して未設定時は ValueError を送出。

### 注意事項 / 実装上の設計方針（重要）
- ルックアヘッドバイアス防止:
  - AI スコア/レジーム判定/ETL/リサーチ関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を明示的に渡す設計。
  - prices_daily クエリでは target_date 未満の排他条件などを使用して未来データ参照を防止。

- フェイルセーフ設計:
  - LLM 呼び出し失敗やパース失敗は基本的に例外を上位に投げず、該当処理をスキップして中立値（0.0 等）や空結果へフォールバックする実装が多い。
  - DB 書き込みはトランザクションで囲み、失敗時は ROLLBACK を試行してから例外を再送出。

- 互換性注意:
  - DuckDB の executemany の空リスト制約（例: DuckDB 0.10）に配慮した実装（空チェックを行う）。
  - OpenAI SDK 例外（APIError 等）で status_code の有無が SDK バージョンにより異なる可能性があるため getattr を用いた安全な扱いを採用。

### 既知の制限 / 今後の改善候補
- news_nlp / regime_detector は gpt-4o-mini と JSON Mode を想定しているが、実運用ではモデルの選択やプロンプトチューニングが必要。
- score_news のレスポンスバリデーションは厳密だが、LLM の出力変動により想定外のフォーマットを受けるケースがある（ログ監視を推奨）。
- ETL の品質チェックは quality モジュールに依存（外部実装）。品質問題の自動修復機構は未実装。
- strategy / execution / monitoring パッケージは __all__ で公開されているが、本リリースのコードスニペットにはそれらの具体的実装が含まれていない可能性あり（今後の拡張対象）。

---

この CHANGELOG はコード内容から推測して作成しています。実リリース時は実際のバージョン番号、リリース日、その他の変更点を正式に更新してください。