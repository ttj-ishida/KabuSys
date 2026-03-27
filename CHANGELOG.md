Keep a Changelog
=================
すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトの変更履歴は "Keep a Changelog" の慣例に従っています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-27
------------------

初期リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能、設計上のポイント、実装上の注意点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージ公開（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring（strategy/execution/monitoring は外部公開名として定義済み）。
- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント取り扱いに対応。
  - OS 環境変数（既存の os.environ）を保護する protected 機能、override モード対応。
  - 自動ロード停止用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスでアプリ設定を整理（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル等）。未設定の必須値は明確な ValueError を送出。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- AI 関連機能（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメント（-1.0〜1.0）を得て ai_scores テーブルに書き込む。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC 換算で前日 06:00 ～ 23:30）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄/リクエスト、1銘柄あたりの記事は最大 _MAX_ARTICLES_PER_STOCK=10 件、最大文字数トリム(_MAX_CHARS_PER_STOCK)に対応。
    - API レスポンスの堅牢なバリデーション（JSON 抽出、results リスト構造、コード照合、数値チェック）、不正レスポンスはスキップ。
    - リトライ: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ（設定値: _MAX_RETRIES/_RETRY_BASE_SECONDS）。
    - フェイルセーフ: API エラー時は該当チャンクをスキップし処理継続。部分成功時は対象コードのみ DELETE → INSERT で差し替え（部分失敗で既存スコアを保護）。
    - テスト容易性: _call_openai_api のモック差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等的に書き込む。
    - マクロセンチメントは news_nlp の窓と同様に記事タイトルを抽出して gpt-4o-mini で評価（JSON 出力）。
    - API 呼び出しは独立実装でモジュール間結合を避け、失敗時は macro_sentiment=0.0 として継続。
    - ルックアヘッドバイアス対策: date 関連処理で datetime.today()/date.today() を直接参照せず、prices_daily クエリは target_date 未満のデータのみ使用。
    - リトライ/バックオフ/ロギング実装あり。
- データプラットフォーム機能（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー（market_calendar）管理：営業日判定、next/prev_trading_day、期間内営業日取得、SQ 判定などのユーティリティを提供。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（土日は非営業日扱い）。
    - calendar_update_job により J-Quants から差分取得→保存（バックフィル / 安全性チェックあり）。
    - 利用時の最大探索日数制限で無限ループ防止。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを導入して ETL 実行結果（取得数/保存数/品質問題/エラー等）を一元管理。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェックの設計方針と定数を実装（backfill, lookahead 等）。
    - quality チェックはエラーを収集するが ETL を途中停止させない方式（呼び出し元で最終判断）。
    - _get_max_date などの内部ユーティリティあり。
  - jquants_client との連携を想定した構成（fetch/save 関数の利用を想定）。
- 研究用モジュール（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を DuckDB 上で計算。
    - データ不足時は None を返す設計。
    - すべて prices_daily / raw_financials のみ参照、外部サービスへアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン）、IC（Spearman のランク相関）計算、統計サマリー、ランク付けユーティリティを実装。
    - pandas 等非依存（標準ライブラリで実装）。ランクは同順位を平均ランクに処理。
- 実装の堅牢化 / 運用面
  - DuckDB を主要なローカル分析 DB として利用（関数署名に DuckDB 接続を受け取る）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン、例外時は ROLLBACK の試行と警告。
  - LLM 関連は JSON Mode を期待しつつ、余計なテキスト混入に対して最外の {} を抽出して復元する耐性あり。
  - ルックアヘッドバイアス防止を設計方針として統一（target_date ベースでの処理）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は明確な ValueError を送出して誤使用を防止。

Notes / 既知の制約
- strategy / execution / monitoring の実際の発注ロジックや外部 API 呼び出し（kabuステーションの通信等）は本スコープには含まれていない（パッケージ公開名として定義済み）。本リリースはデータ収集・前処理・研究・AI スコアリングの基盤を中心に実装。
- OpenAI 呼び出し部分は外部サービスに依存するため、本地環境での動作には OPENAI_API_KEY とネットワークアクセスが必要。
- DuckDB の executemany 周りのバージョン差異（空リスト不可等）に配慮した実装がされているが、実運用で接続先バージョンによる差異が出る可能性あり。
- カレンダー更新は J-Quants クライアント実装（jquants_client.fetch_market_calendar / save_market_calendar）に依存するため、実装済みクライアントが必要。

Contributors
- 初期実装（1.0 相当）のコードベースをまとめて追加。

---

今後の予定（例）
- strategy / execution の発注ロジック実装（paper/live 切替を含む）とエンドツーエンド統合テスト。
- monitoring（アラート・Slack 連携）の実装強化。
- テストカバレッジ向上（ユニットテスト・統合テスト）、CI の整備。