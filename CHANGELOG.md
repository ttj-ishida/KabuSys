Keep a Changelog
=================

すべての重要な変更点をここに記載します。  
このファイルは「Keep a Changelog」形式に準拠しています。

[Unreleased]: https://example.com/kabusys/compare

0.1.0 - 2026-03-27
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py
      - バージョン: 0.1.0
      - エクスポート: data, strategy, execution, monitoring

- 環境設定 / 設定管理
  - src/kabusys/config.py
    - .env ファイルや環境変数からの設定読み込み機能を実装。
    - プロジェクトルートの検出: __file__ を起点に .git または pyproject.toml を探索して自動的にルートを特定（配布後も CWD に依存しない実装）。
    - 自動ロード優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサ: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント（#）の扱いなどを考慮した堅牢なパース処理。
    - Settings クラスを提供し、アプリケーション設定（J-Quants、kabuステーション、Slack、DB パス、環境モード、ログレベル等）をプロパティ経由で取得。
    - env / log_level の入力検証（許容値チェック）と is_live / is_paper / is_dev の利便性プロパティ。

- ニュースNLP と マーケットレジーム判定（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON モード）へバッチ送信してセンチメントスコア（-1.0〜1.0）を取得、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ/トリム戦略:
      - バッチサイズ: 20 銘柄 / API コール
      - 最大記事数: 1 銘柄あたり最新 10 件
      - 最大文字数: 1 銘柄あたり 3000 文字（超過分はトリム）
    - リトライ方針: RateLimit / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（最大設定あり）、その他はスキップしてフェイルセーフに継続。
    - レスポンスバリデーション: JSON パース、"results" の構造チェック、未知コードの無視、スコア数値性と有限性チェック、±1.0 にクリップ。
    - DuckDB 互換性: executemany の空リスト送信回避（DuckDB 0.10 への注意）。
    - ログ出力（進捗・警告・エラー）を充実させ、API 失敗時は該当チャンクをスキップする設計。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - 主な定数/設計:
      - MA ウィンドウ: 200 日、スケール係数 10、MA 重み 0.7、マクロ重み 0.3
      - マクロ検出キーワード群（日本・米国等）を用いて raw_news からタイトルを抽出（最大 20 件）
      - OpenAI モデル: gpt-4o-mini、JSON モード、temperature=0、timeout=30
      - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
      - レジームスコアのクリップ処理とラベリング閾値（bull / bear 判定閾値）
    - DB 書き込みは冪等: BEGIN → DELETE WHERE date = ? → INSERT → COMMIT。失敗時は ROLLBACK（失敗ログを出力）して例外を再送出。

  - 共通特長（AI モジュール）
    - OpenAI 呼び出しは専用の内部関数でラップしており、テスト時はパッチ差し替え可能。
    - JSON Mode を想定した厳格なレスポンス処理と復元ロジック（最外の {} 抽出など）を実装。
    - API エラー種別ごとの挙動を詳細に制御（RateLimit / Connection / Timeout / 5xx のリトライ等）。

- データプラットフォーム / ETL / カレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ユーティリティを実装（market_calendar テーブルを用いた営業日判定、next/prev/get_trading_days、is_sq_day 等）。
    - DB にカレンダー情報がない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - _MAX_SEARCH_DAYS により next/prev の探索上限（無限ループ防止）を設定（デフォルト 60 日）。
    - 夜間バッチ calendar_update_job:
      - J-Quants API から差分取得（lookahead/backfill により最新性と訂正取り込みを考慮）
      - 健全性チェック（未来日付が不自然に遠い場合はスキップ）
      - jq.fetch_market_calendar / jq.save_market_calendar を用いた取得・保存の流れ
      - 取得/保存結果のログとサマリ返却

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックのインターフェース実装。
    - ETLResult（dataclass）を公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - ETLResult により取得件数、保存件数、品質チェック結果、エラー概要を集約。has_errors / has_quality_errors / to_dict を提供。
    - 内部ユーティリティ:
      - テーブル存在チェック、最大日付取得、market calendar への調整ロジック等を実装。
    - 設計上の配慮:
      - 差分更新は営業日単位をデフォルトとし、backfill により API の後出し修正を吸収。
      - 品質チェックで重大エラーが出ても ETL は継続して結果を収集（呼び出し元で判断）。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター群の計算ロジックを実装（prices_daily / raw_financials を使用）。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
      - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率
      - Value: PER、ROE（raw_financials の最新レコードを target_date 以前から選択して使用）
    - DuckDB によるウィンドウ関数活用で効率的に算出。データ不足時は None を返す設計。
    - 出力は [{"date", "code", ...}] の形式で返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）に対するリターンを LEAD で一括取得。
    - IC（Information Coefficient）計算（calc_ic）: ファクター値と将来リターンの Spearman（ランク相関）計算。データ不足（有効レコード < 3）時は None を返す。
    - ランク関数（rank）: 同順位は平均ランクにし、浮動小数の丸め（round(..., 12)）で ties の検出漏れを防止。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出（None 値除外）。

- 内部品質・安全性
  - 多くの箇所で「ルックアヘッドバイアス防止」の設計を採用（datetime.today() / date.today() を直接参照せず、target_date ベースの計算を行う）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、失敗時に ROLLBACK を試みる。ROLLBACK 失敗時は警告ログを出力。
  - 外部 API 依存箇所（OpenAI / J-Quants）はエラー耐性を持ち、フェイルセーフで処理を継続する方針。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記
- OpenAI API キーは関数引数で注入可能（テスト容易性）で、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError を送出します。
- DuckDB のバージョン依存（executemany の空リスト扱いなど）を考慮した互換性対策が多数含まれています。
- 実運用では J-Quants / kabu API / Slack 等の各種資格情報設定およびロギング設定が必要です（config.Settings を参照）。

今後の予定（例）
- strategy / execution / monitoring の詳細実装と実運用向けの安全策（サーキットブレーカー、発注シミュレーション等）。
- モデル評価パイプラインやバックテスト用ユーティリティの拡張。