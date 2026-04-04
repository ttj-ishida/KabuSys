Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の慣習に従っています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

（なし）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース。
- 基本パッケージ公開
  - kabusys.__init__ により主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理 (kabusys.config)
  - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動検出（カレントワーキングディレクトリに依存しない）。
  - .env 自動読み込み機構:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - ファイル読み込み失敗時に警告を発行して継続。
    - 既存 OS 環境変数を保護するため protected キーセットを使用して上書き制御。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理などを実装。
  - Settings クラス: J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。バリデーション（列挙値チェック、必須キーチェック）を含む。
  - デフォルト値（例: KABUSYS_API_BASE_URL やデータベースパス、PID / kill flag のパスなど）を備える。
- AI 関連機能 (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols に基づき、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ保存する機能を実装。
    - ニュース時間ウィンドウ定義（JST 前日 15:00 ～ 当日 08:30、UTC で変換）を calc_news_window 関数で提供。
    - バッチ/チャンク処理（デフォルト 20 銘柄 / チャンク）、1銘柄あたり最大記事数・最大文字数トリム、チャンク内での再試行（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - API レスポンスの厳密バリデーション（JSON 抽出、results 配列の検査、コード整合性、スコア数値性）、スコアを ±1.0 にクリップ。
    - テスト用の差し替えポイント: _call_openai_api をモック可能。
    - ai_scores への書き込みは部分失敗に備え、該当コードのみ DELETE → INSERT（冪等/保護）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動）200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルに書き込み。
    - ma200_ratio 計算は target_date 未満のデータのみ使用し、データ不足時は中立値（1.0）にフォールバックして警告をログ出力。
    - マクロ記事抽出はタイトルベースでキーワードフィルタを適用（最大検索記事数制限）。
    - OpenAI 呼び出しでのリトライ（429/ネットワーク/タイムアウト/5xx）とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - スコア合成ロジック（スケールと閾値による bull/neutral/bear ラベル付け）。
    - market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - テスト用に _call_openai_api を差し替え可能。
- Research / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を DuckDB SQL で計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（平均）、ATR の相対値、20 日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials からの EPS/ROE 組合せで PER/ROE を算出（報告日以前の最新データを使用）。
    - 実装は DuckDB 上で完結し、外部 API へのアクセスなし（研究環境向け）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
    - calc_ic: Spearman（ランク）による IC（Information Coefficient）計算（結合と欠損除外、3 銘柄未満で None）。
    - rank: 平均ランク処理（同順位は平均ランク扱い、丸め処理による ties 対応）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリで算出。
  - research パッケージは研究向けユーティリティ群を公開（zscore_normalize を data.stats から再利用）。
- Data / カレンダー・ETL (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 次/前営業日の探索は最大探索日数制限で無限ループ防止。
    - calendar_update_job: J-Quants クライアント経由で差分取得し、バックフィル（直近数日を再フェッチ）と健全性チェックを行った上で DB に保存。
  - pipeline / ETL:
    - ETLResult データクラスで ETL の取得数・保存数・品質問題・エラーを集約。
    - ETL パイプライン: 差分更新・バックフィル・idempotent 保存（jquants_client の save_*）・品質チェック（quality モジュールとの連携）を想定した設計。
    - quality_issues をシリアライズ可能に変換する to_dict 実装。
    - デフォルトのバックフィル日数やカレンダー先読み等の定数を提供。
  - jquants_client との連携を前提とした設計（fetch / save を呼び出す箇所を用意）。

Security
- 特になし（本バージョンは初回公開）。ただし OpenAI API キーや各種トークンは必須の環境変数として管理。

Fixed
- 初回リリースにつき過去のバグ修正はなし。ただし多くの箇所でフェイルセーフ（API 失敗時に例外を投げず 0 や空で継続）やログ出力による可観測性強化を実装。

Notes / 既知の制限・設計方針
- ルックアヘッドバイアス防止:
  - すべての「日付基準」処理は date / target_date を明示的に受け取り、datetime.today() / date.today() の直接参照を避ける設計。
- テスト性の考慮:
  - OpenAI 呼び出し部分にモック差し替えポイントを提供（_call_openai_api を patch 可能）。
  - .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 依存:
  - duckdb, openai（OpenAI Python SDK）を想定。
  - Python 3.10 以降（| 型ヒントを使用）。
- デフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID / KILL flag: data/execution.pid / data/kill.flag
- ログレベル・環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれか（不正な値でエラー）。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか（不正な値でエラー）。

Breaking Changes
- なし（初回リリース）。

Authors
- コードベースから推測した設計意図に基づく CHANGELOG（生成: 自動推測）。

-- end --