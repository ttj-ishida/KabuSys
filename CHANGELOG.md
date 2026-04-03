# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
このファイルはコードベース（初期リリース相当）の内容から推測して作成しています。

- ページ: 変更履歴を分かりやすく保つため、リリースごとに主要な追加・変更点および注意点を列挙しています。
- 日付: このドキュメントは 2026-04-03 時点のコード内容に基づいて作成しています。

## [Unreleased]
- なし（初期リリースのみ存在）

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ = "0.1.0" を設定。

- 設定・環境変数管理 (kabusys.config)
  - .env 自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントルール等に対応。
  - _load_env_file にて protected（既存 OS 環境変数）を上書きしない安全機構を実装。
  - Settings クラスを提供し、アプリ設定をプロパティベースで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知関連）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（監視用デフォルト data/monitoring.db）
    - 監視関連ファイルパスとしきい値（PID/KILL フラグ/CPU/MEM/DISK）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）および LOG_LEVEL のバリデーション
    - 環境に応じたユーティリティプロパティ: is_live, is_paper, is_dev

- データプラットフォーム（kabusys.data）
  - カレンダー管理モジュール（calendar_management）
    - JPX マーケットカレンダー管理: market_calendar 参照/更新、夜間バッチ calendar_update_job 実装。
    - 営業日判定・検索ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベースでフォールバック（週末は非営業日）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS)、先読み・バックフィル・健全性チェックを実装。
    - jquants_client によるフェッチ/保存インターフェースを利用。

  - ETL パイプライン（pipeline / etl / etl 結果クラス再公開）
    - ETLResult データクラス（取得数・保存数・品質問題・エラーを保持）を実装し、kabusys.data.etl で再エクスポート。
    - pipeline モジュール方針: 差分更新、バックフィル、品質チェック（quality モジュール連携）等の設計ノートを実装（実際の ETL 実行ロジックの骨組みを含む）。
    - DuckDB を主体とした差分取得／保存のユーティリティを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols からニュースを集約して銘柄ごとにセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む score_news 関数を実装。
    - 時間ウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（DB 比較は UTC naive datetime に変換）を採用。
    - OpenAI（gpt-4o-mini）を JSON mode で呼び出し、最大バッチサイズ 20 銘柄でチャンク処理。
    - 1 銘柄当たり記事個数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装しトークン肥大化に対応。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフリトライ、その他はスキップして継続。レスポンスバリデーションを実装（results 配列・コード照合・数値チェック・クリッピング）。
    - DuckDB への書き込みは部分的置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護を考慮。
    - テストしやすさ: _call_openai_api はモック差し替え可能（unittest.mock.patch）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - LLM 呼び出しは独立実装（news_nlp と内部関数を共有しない）でモジュール結合を最小化。
    - マクロ記事フィルタリング用キーワード群を実装し、最大記事件数・リトライ等を設定。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m/3m/6m、ma200_dev（必要行数未満は None）
      - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio（窓不足は None）
      - calc_value: per（EPS が 0/NULL の場合 None）、roe（raw_financials から）
    - DuckDB SQL を主体に実装し、外部 API にはアクセスしない設計。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns（horizons デフォルト [1,5,21]、入力検証あり）。
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関、最小有効レコード数チェック）。
    - rank、factor_summary: ランク変換（同順位は平均ランク、丸め処理）と統計サマリを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

- モジュールの公開 API
  - 主要関数をモジュールエクスポート（news_nlp.score_news, ai.score_regime, research.* の各種関数等）。
  - test-friendly な設計（OpenAI 呼び出しを抽象化しモック化を簡易に）。

### 変更 (Changed)
- 初回リリースのためなし（新規実装群）。ただし以下のデフォルト設定や実装方針が含まれる点に注意:
  - デフォルト DB パス / API ベース URL / ニュースウィンドウ等はコード内定数として固定されている。
  - OpenAI モデルは gpt-4o-mini を使用する設計（JSON mode を期待）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- .env の自動読み込みは既存 OS 環境変数を上書きしない保護機構を導入（protected set）。
- API キー（OPENAI_API_KEY 等）が未設定の場合、明示的に ValueError を発生させる安全設計（誤動作の早期発見）。
- 環境変数自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供し、テストや CI 環境でのキー漏洩リスクを低減。

### 既知の制限 / 注意点 (Known limitations / Notes)
- OpenAI とのやり取りは JSON mode を前提にしているが、実運用では稀に余計なテキストが混入する想定で復元ロジックを実装している（前後の {} を抽出してパース）。
- DuckDB の executemany に空リストを渡せないバージョン対応として、空チェックを行った上で実行している。
- 日付取り扱いはルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を直接参照しない（target_date を外部から渡す設計）。
- score_news / score_regime は OpenAI API キーの注入（api_key 引数）をサポートするが、キーが未設定だとエラーになるため運用時に環境設定が必須。
- 一部計算（例: PBR・配当利回り）は未実装（calc_value の Note に記載）。
- calendar_update_job は J-Quants クライアント（jquants_client）の fetch/save 実装に依存する（外部 API 呼び出しに失敗すると 0 を返す）。

---

今後のリリースでは以下が検討候補です（コード内容からの推測）:
- PBR・配当利回りなどのバリューファクターの追加実装。
- より細かい監視・運用ツール（LINE 通知・モニタリング周りの強化）。
- OpenAI モデル切替やトークン最適化、バッチ処理の最適化。
- ETL の実働ワークフローと品質チェックの自動アクション化。

もし CHANGELOG のスタイルや記載の粒度について希望があれば指示ください。必要であれば英語版やセクション分割（内部API / public API / DB スキーマ変更点など）も作成します。