Keep a Changelog
=================

すべての変更は "Unreleased" → バージョン履歴の順に記載します。  
このファイルは Keep a Changelog の慣例に準拠しています。

[0.1.0] - 2026-03-27
-------------------

Added
- 初期リリース。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 公開モジュール: data, research, ai, config, など主要サブパッケージをエクスポート。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサは export プレフィックスやシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 必須設定取得用の _require と Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - 環境変数の保護機構（OS 環境変数を protected として上書き防止）。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント（score_news）: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 参照）。
    - バッチ/チャンク処理: 1 API 呼び出しあたり最大 20 銘柄（_BATCH_SIZE=20）。
    - 1 銘柄あたり最大 10 記事、文字数上限 3000（トリム）でトークン肥大化対策。
    - JSON Mode を用いた厳密な JSON 出力期待とレスポンスバリデーション。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ。
    - API 失敗やレスポンス不正時はフェイルセーフで該当チャンクをスキップし、処理継続。
    - DuckDB への書き込みは冪等性を保ち、部分失敗時に既存データを保護（DELETE → INSERT、対象コードを限定）。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）へ投げて -1..1 のスコアを取得。
    - ルックアヘッドバイアス回避のため、target_date 未満のデータのみ使用。
    - API 呼び出しはリトライ／バックオフを実装、最終的な API 失敗時は macro_sentiment=0 をフォールバック。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- Data（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを参照して営業日判定を行うユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバック。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants から差分取得して保存（バックフィルと健全性チェックあり）。
    - 探索範囲の上限を設け無限ループを防止（_MAX_SEARCH_DAYS=60 など）。

  - ETL パイプライン（pipeline）
    - DataPlatform の方針に沿った差分取得・保存・品質チェックのための基盤コードを提供。
    - ETLResult dataclass による実行結果集約（取得件数、保存件数、品質問題、エラー等）。
    - デフォルトの backfill や calendar lookahead などの設定を実装。
    - data/etl は ETLResult を再エクスポート。

- Research（src/kabusys/research）
  - ファクター計算（factor_research）
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）
    - Volatility/Liquidity: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）
    - Value: PER（株価/EPS）、ROE（raw_financials からの取得）
    - DuckDB を用いた SQL ベースの実装。データ不足時は None を返す等の頑健性を確保。
    - 公開関数: calc_momentum, calc_volatility, calc_value

  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応。ホライズンは営業日ベース。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装。3件未満は None を返す。
    - ランク変換ユーティリティ（rank）および統計サマリー（factor_summary）。

- 実装方針（全体で共通）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を内部処理で不用意に参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主要なローカル分析用 DB として使用（src 中で duckdb 型注釈あり）。
  - OpenAI SDK（OpenAI クライアント）を使用。モデルは gpt-4o-mini を想定。
  - API 呼び出し失敗時は全体を停止させず、フェイルセーフ（0.0 やスキップ）で継続する方針。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当の設計）を採用。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- OpenAI / 外部 API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を利用。キー未設定時は ValueError を明示的に発生させることで誤動作を防止。

注意事項 / マイグレーション
- 初期リリースのため既存互換性に関する破壊的変更はありません。
- 環境変数の名称や Settings API を用いることで、設定は .env あるいは環境変数から読み込む前提です。必須変数（例: OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を環境に設定して利用してください。
- DuckDB のテーブルスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等）が前提となります。初回利用時はスキーマ作成・データロードが必要です。

問い合わせ / コントリビューション
- バグ報告・提案は issue を立ててください。設計方針（ルックアヘッド回避、冪等書き込み、フェイルセーフ等）を尊重した設計で PR を歓迎します。