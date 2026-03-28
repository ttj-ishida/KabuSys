# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

リンクや比較参照は省略しています。リリース日はコードから推測した初期リリース日（本ファイル生成日）を使用しています。

## [Unreleased]
- 

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - public API として data, strategy, execution, monitoring をエクスポート

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
      - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に検出
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - .env パーサーは以下をサポート
      - コメント行/空行、export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ
      - クォートなしの値内でのインラインコメント処理（直前が空白/タブの場合）
    - Settings クラスを提供（settings インスタンスをエクスポート）
      - 必須環境変数の検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - デフォルト値付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値をチェック）
      - ヘルパープロパティ: is_live / is_paper / is_dev

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_score）を算出
    - 機能ハイライト:
      - ニュース集計ウィンドウ（JST 基準の前日 15:00 〜 当日 08:30）を calc_news_window で計算
      - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - 銘柄を最大 20 件ずつバッチ送信（_BATCH_SIZE）
      - JSON Mode のレスポンス検証（結果の構造・数値性を検証し ±1.0 にクリップ）
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装
      - スコア書き込みは部分失敗を避けるため対象コードのみ DELETE→INSERT の冪等置換
      - スキップ時はフェイルセーフ（例外を上げずにスキップして継続）
    - 公開関数: score_news(conn, target_date, api_key=None)

  - src/kabusys/ai/regime_detector.py
    - マーケットレジーム判定（'bull' / 'neutral' / 'bear'）
    - 手法:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成
      - レジームスコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
      - 閾値に基づきラベルを決定（_BULL_THRESHOLD / _BEAR_THRESHOLD）
    - マクロニュースの抽出はキーワードベース（複数日本語・英語キーワードを定義）
    - OpenAI への呼び出しは独立した内部実装でモジュール結合を避ける
    - API エラー時は macro_sentiment=0.0 とするフェイルセーフ
    - public: score_regime(conn, target_date, api_key=None)

- データプラットフォーム関連
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基本構造を実装（差分取得・保存・品質チェックを想定）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー集約）
    - DB の最大日付取得などのユーティリティを提供
    - J-Quants クライアント（jquants_client）との統合箇所を想定（差分取得・保存を委任）
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート
  - src/kabusys/data/calendar_management.py
    - JPX（市場）カレンダー管理と営業日判定ロジックを実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
      - market_calendar テーブルが未取得の場合は曜日ベースでフォールバック（週末除外）
      - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）
    - 最大探索日数やバックフィル日数等の安全設計を実装

- リサーチ（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value, Liquidity 系の因子計算を実装
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率
      - calc_value: PER（price/EPS）、ROE（raw_financials からの最新値）
    - 全て DuckDB の prices_daily / raw_financials テーブルを参照し外部 API に依存しない設計
    - 結果は (date, code) をキーにした dict リストで返却
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Information Coefficient）計算: calc_ic（Spearman ρ 相当、ランク化を内蔵）
    - rank 関数（同順位は平均ランク）および factor_summary（count/mean/std/min/max/median）を実装
    - pandas 等に依存しない純 Python 実装を採用
  - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize の再利用含む）

- 内部ユーティリティ・設計文書化
  - 各モジュールに設計方針やフェイルセーフの説明コメントを充実させ、テストで差し替えやすいように _call_openai_api などを分離実装
  - DuckDB を主要ストレージとして使用する想定で SQL クエリ設計

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Deprecated
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- OpenAI API キーの扱い:
  - API キーは関数引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照。
  - 必須未設定時は明示的に ValueError を投げることで誤操作に気付きやすくしている。

---

注記（実装上の重要ポイント / マイグレーションガイド）
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用し厳密な JSON 出力を期待するが、実運用では外側の余分なテキストを許容する復元ロジックを入れているため堅牢性がある。
- AI モジュールは API の一時エラーに対して指数バックオフを行う実装だが、最終的に失敗した場合は該当データをスキップ（0 や空辞書でフォールバック）するため「取得失敗 = その日のデータ欠損」が起きうる点に注意。
- DuckDB の executemany に関する互換性（空リストを渡せない等）を考慮した実装になっている。
- カレンダーや ETL はバックフィルや健全性チェックを含み安全設計を優先しているため、運用時は lookahead/backfill のパラメータを調整してください。

以上。