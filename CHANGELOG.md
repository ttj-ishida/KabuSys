# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリポジトリ内のバージョン情報（__version__ = "0.1.0"）および現行スナップショット内容に基づき記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期リリース「kabusys」。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - パブリックモジュール群を __all__ で公開: data, strategy, execution, monitoring。

- 環境変数/設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定値を自動ロードする仕組みを実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - プロジェクトルートの検出は __file__ を起点に .git / pyproject.toml を探索（CWD に依存しない）。
  - .env パーサー実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、
      インラインコメントの取り扱い、無効行（空行、#で始まる行）のスキップに対応。
  - Settings クラスを提供し、アプリ固有設定をプロパティ経由で取得可能:
    - J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）など。
    - 環境変数未設定時にエラーを送出する `_require` を実装（必須設定の明示）。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証ロジック。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI 系ユーティリティ（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント判定を行い ai_scores テーブルへ保存する機能。
    - 処理フロー: ウィンドウ計算 → 記事集約（最大記事数・文字数でトリム）→ バッチ（最大 20 銘柄/チャンク）で API コール → レスポンス検証 → ai_scores へ置換（DELETE → INSERT）。
    - エラーハンドリング: 429/ネットワーク切断/タイムアウト/5xx に対する指数バックオフによるリトライ、API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション: JSON 抽出、results リストの構造検証、unknown code の無視、スコアを ±1.0 にクリップ。
    - DuckDB の executemany の制約（空リスト不可）を考慮した実装。
    - calc_news_window 関数を提供（JST ベースのニュース収集ウィンドウを UTC naive datetime で返す）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能。
    - 処理詳細:
      - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立=1.0 を使用）。
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出（最大 20 件）。
      - OpenAI（gpt-4o-mini）に JSON モードで問い合わせて macro_sentiment を取得、失敗時は 0.0 をフォールバック。
      - スコア合成と閾値判定（BULL / BEAR の閾値設定）。
      - DB への冪等書き込みは BEGIN / DELETE / INSERT / COMMIT（失敗時に ROLLBACK）。
    - OpenAI 呼び出しは内部関数化し、モジュール間でプライベート関数を共有しない設計。

- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ロジックを実装。
    - market_calendar が未取得のときの曜日ベースのフォールバック。
    - 最大探索日数制限や健全性チェック、バックフィル戦略の実装。
    - calendar_update_job により J-Quants から差分取得して market_calendar を更新するバッチ機能を実装（バックフィルと健全性チェックを含む）。
    - jquants_client 経由での取得/保存処理を想定。

  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - 差分取得・保存（idempotent 保存）・品質チェック（quality モジュール）を行う設計方針を実装。
    - デフォルトバックフィル、カレンダー先読み、最小データ開始日などの定数を定義。
    - DB 上の最大日付取得やテーブル存在確認などのユーティリティを実装。

- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER/ROE）の計算関数を提供。
    - DuckDB 上で SQL とウィンドウ関数を活用して効率的に計算。
    - 必要データ不足時の None 戻しやログ出力を行う等、堅牢な設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（可変ホライズン、入力検証、単一クエリ取得）。
    - IC（Information Coefficient）を計算する calc_ic（スピアマンの順位相関を内部実装）。
    - rank（同順位は平均ランクに処理）、factor_summary（count/mean/std/min/max/median）を提供。
  - research パッケージの __init__ で主要関数を再エクスポート。

### Changed
- 設計方針として共通で以下を明確化:
  - ルックアヘッドバイアス防止のため、date.today()/datetime.today() を関数内部で参照せず、必ず target_date を引数で受け取る設計。
  - DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT 想定）を採用。
  - 外部 API（OpenAI / J-Quants 等）失敗時は「フェイルセーフで続行」する挙動を基本方針とし、致命的なエラーのみ上位へ伝播する。

### Fixed
- DuckDB の executemany に空リストを渡すと失敗する挙動への対策を実装（empty check を追加）。
- OpenAI レスポンスパースの堅牢化:
  - JSON mode でも前後の余計なテキストが混入するケースに対応して、最外の {} を抽出して再試行するロジックを追加。
  - レスポンスの型検証と未知コード無視、スコア数値検証を追加して不正レスポンスによる破壊的影響を防止。
- regime_detector と news_nlp の API 呼び出しに対してリトライ/バックオフ/フォールバック（macro_sentiment=0.0、チャンクスキップ）を導入し、外部サービス不安定時の堅牢性を改善。
- market_calendar の NULL 値取り扱い時に警告ログを出力し、曜日ベースのフォールバックに一貫性を持たせた。

### Security
- 設定ロードで OS 環境変数を保護するため、.env 読み込み時に既存 OS 環境変数のセットを protected として上書きを制御する実装を追加（_load_env_file の protected 引数）。
- 必須の API キー（OpenAI 等）を未設定で処理を開始しないよう ValueError を投げる箇所を明確化（明示的な fail-fast ポイント）。

### Notes / Known limitations
- OpenAI 呼び出しは現時点で gpt-4o-mini を前提に実装している（モデル変更はパラメータ修正が必要）。
- news_nlp の出力は現フェーズでは sentiment_score と ai_score を同値で格納している（将来的に差分化の余地あり）。
- calendar_update_job / ETL の外部依存（jquants_client, quality モジュール）はクライアント側の実装に依存するため、環境ごとの差異に注意。
- DuckDB 固有のバインドや型挙動に依存する部分があるため、DuckDB バージョン差異に注意（実装中で互換性対策あり）。

---

この CHANGELOG はリポジトリ内コード構成・コメントから推測して作成しています。実際のコミット履歴や意図と異なる場合があります。必要であれば、個別モジュールごとの詳細な変更点（関数行数やコミット単位）を確認して更新します。