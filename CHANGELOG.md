CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。重要: 下記内容は与えられたコードベースから推測して作成したリリースノートです。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- 全体
  - 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージ公開インターフェースを定義（src/kabusys/__init__.py）。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 読み込み優先度: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ実装: export 形式、クォート・エスケープ、インラインコメントの考慮。
  - protected オプションを用いた既存 OS 環境変数保護（上書き回避）。
  - Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントスコアを付与。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 に対応した UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大20銘柄／リクエスト）、銘柄ごとの記事数・文字数トリム、レスポンス検証、±1.0 でクリップ。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。
    - レスポンスパースのロバスト化（JSON mode の前後ノイズ検出と {} 抽出）。
    - 書込みは ai_scores テーブルに対して idempotent に DELETE → INSERT を実行（部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch 推奨）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し日次でレジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算、マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0（フェイルセーフ）として継続。
    - OpenAI API 呼び出しに対するリトライ（rate/conn/timeout/5xx）とログ記録。
- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを使った営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得・保存件数、品質チェック結果、エラー集約など）。
    - 差分更新・バックフィルの方針、品質チェックの扱い（重大度を報告するが処理は継続）を実装。
  - DuckDB 周りの互換性と安全な SQL 実行（テーブル存在チェック、日付の変換ユーティリティ等）を提供。
- Research モジュール (src/kabusys/research)
  - factor_research.py:
    - モメンタム（1/3/6 か月リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 不足データ時の None 返却、営業日スキャンのバッファ等を考慮。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman のランク相関）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
  - research パッケージ __init__ で主要 API を再エクスポート。
- 再エクスポート / API
  - data.etl から ETLResult を再エクスポート。
  - ai パッケージで score_news を公開。

Changed
- 設計上の留意点（ドキュメント化）
  - 各種処理で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）を明確化。
  - DuckDB のバージョン差異（executemany の空リスト制約、リストバインドの互換性）を考慮した実装。

Fixed
- （初回リリースのためなし。コード内にロバスト化措置やログ出力強化を多数導入）

Security
- 環境変数周りの取り扱いを明確化:
  - 必須環境変数が未設定の場合は ValueError を送出（Settings の各必須プロパティ）。
  - .env ファイルの読み込みエラーは警告ログで処理し、例外は波及しない設計（堅牢化）。
  - OPENAI_API_KEY は明示的に引数で注入可能。外部からの注入によりテスト/運用での秘密情報管理が容易。
- DB 操作は明示的なトランザクション（BEGIN/DELETE/INSERT/COMMIT）を用い、失敗時は ROLLBACK を試行してログ出力。

Notes / Known limitations
- ファクター: PBR や配当利回りは現バージョンでは未実装（calc_value に明記）。
- AI レスポンスの検証は強化しているが、LLM の想定外出力への耐性は完璧ではないため運用時のモニタリング推奨。
- news_nlp の JSON parsing は前後ノイズを検出して復元を試みるが、完全なサニティチェックは運用でのログ確認を推奨。
- DuckDB を前提とした実装になっている（型や executemany の挙動に注意）。

Migration
- なし（初回リリース）。ただし既存の運用環境では必要な環境変数を設定の上、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動環境読み込み無効化オプションを確認してください。

開発者向けメモ
- テストの容易性のため、OpenAI 呼び出し部分（kabusys.ai.news_nlp._call_openai_api／kabusys.ai.regime_detector._call_openai_api）をモック差し替え可能。
- ロギングは多箇所で行っているため、運用時は適切なログレベル（LOG_LEVEL）を設定して監視してください。

以上。必要であれば、より詳細なセクション分割（関数別、ファイル別の変更一覧）や、リリースごとの差分比較を追加で作成します。