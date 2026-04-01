# Keep a Changelog 変更履歴

すべての変更は https://keepachangelog.com/ja/ の慣習に従って記述しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。

### 追加
- パッケージの基本構成を追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 主要サブパッケージをエクスポート: data, strategy, execution, monitoring。

- 環境設定・読み込み機能を実装（src/kabusys/config.py）。
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - export KEY=val 形式、クォート・エスケープ、インラインコメントの取り扱いに対応したパーサを実装。
  - 自動読み込みを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected オプションをサポート（.env.local の上書き制御含む）。
  - 必須環境変数チェック用の _require() と Settings クラスを提供。
  - J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを実装。
  - LOG_LEVEL / KABUSYS_ENV のバリデーション（許容値チェック）を実装。

- AI 関連機能を追加（src/kabusys/ai/ 以下）。
  - ニュース NLP: src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - チャンク処理、最大記事数・文字数トリム、バッチサイズ、JSON レスポンスの堅牢なバリデーションを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - API 呼び出し箇所はテスト時に差し替え可能な設計（_call_openai_api の patch を想定）。
    - ルックアヘッドバイアス回避: datetime.today() を参照しない設計。
  - 市場レジーム判定: src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離およびマクロニュース LLM センチメントを組み合わせて日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース取得（キーワードフィルタ）、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアの合成ロジック（MA 重み 70%、マクロ重み 30%）を実装。
  - ai/__init__.py で score_news を公開。

- リサーチ用解析機能を追加（src/kabusys/research/ 以下）。
  - ファクター計算: src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高変化率）を計算する関数を実装。
    - DuckDB による SQL + Python のハイブリッド実装で、prices_daily / raw_financials テーブルのみを参照。
    - データ不足時の None 扱いやログ出力等の耐障害性を考慮。
  - 特徴量探索: src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズン）、IC（Spearman rank correlation）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
    - 外部ライブラリに依存しない純 Python 実装。
  - research/__init__.py で主要関数を再エクスポート。

- データプラットフォーム関連を追加（src/kabusys/data/ 以下）。
  - カレンダー管理: src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）に対する夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB の存在確認・未登録日の曜日ベースフォールバック、最大探索日数などの安全策を実装。
    - J-Quants クライアント経由で差分取得・保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
  - ETL パイプライン・ユーティリティ: src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL の結果を表す ETLResult dataclass を実装（品質チェック結果・エラー一覧の保持、辞書化メソッドを提供）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映。
    - data/etl.py で ETLResult を再エクスポート。
  - jquants_client（参照）との連携箇所を想定した設計。

### 変更
- なし（初回リリースのため変更履歴は追加項目が主体）。

### 修正（設計上の堅牢化）
- データベース書き込みにおけるトランザクション安全性を考慮（BEGIN / DELETE / INSERT / COMMIT、失敗時の ROLLBACK と警告ログ）。
- DuckDB の executemany に関する既知の制約（空リスト不可）を回避するチェックを追加（ai/news_nlp.py 等）。
- OpenAI API のエラー処理を詳細化（429・接続・タイムアウト・5xx のリトライ、非5xx は即座にフォールバック）。
- JSON レスポンスのパース耐性を向上（前後余計なテキストが混ざるケースの復元ロジック等）。
- ルックアヘッドバイアスを防ぐ設計方針を明確化（datetime.today() を直接参照しない、対象日を明示的に受け取る）。

### 既知の制限
- OpenAI API を利用する機能は API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する設計。
- 一部処理は DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提とする。
- 本バージョンでは Strategy / Execution / Monitoring の実装詳細はパッケージ構成として用意されているが、本 CHANGELOG のソースに含まれるのは主にデータ・リサーチ・AI 側の実装。

---

将来的なリリースでは、発注（execution）やストラテジー定義、モニタリングの具体実装、単体テスト・統合テストスイート、ドキュメント（使用例・セットアップ手順）を順次追加する予定です。