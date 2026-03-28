# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
初期バージョン 0.1.0 をリリースしました。

## [Unreleased]

## [0.1.0] - 2026-03-28

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 読み込みルール:
    - export KEY=val 形式に対応
    - シングル/ダブルクオート内のバックスラッシュエスケープ処理をサポート
    - クォートなし行のインラインコメント処理（# の直前が空白またはタブのときのみコメントと認識）
    - 読み込み時に OS 環境変数を保護する protected キー集合の扱い、override オプション
  - Settings クラスを提供:
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティ（必須項目は未設定時に ValueError）
    - KABUSYS_ENV の検証（development/paper_trading/live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパープロパティ
- AI 関連 (src/kabusys/ai/)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode で銘柄ごとのセンチメントスコアを取得
    - バッチ処理（最大 20 コード/チャンク）、1銘柄あたり記事トリム（最大記事数・最大文字数）でトークン肥大化を制御
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ、その他エラーはスキップでフェイルセーフ
    - レスポンスバリデーション（JSON 抽出、"results" フォーマット、未知コード無視、数値変換、±1.0クリップ）
    - calc_news_window(target_date) を実装（JST: 前日15:00～当日08:30 を UTC に変換した半開区間）
    - score_news(conn, target_date, api_key=None): 書き込みは冪等（DELETE→INSERT）、部分失敗時に他コードのスコアを保護
    - テスト容易性: OpenAI 呼び出し関数はパッチ可能（_call_openai_api を差し替え可能）
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジームを判定（bull/neutral/bear）
    - マクロニュース抽出はマクロキーワード群でフィルタ、上限記事数適用
    - OpenAI 呼び出しは JSON Mode、リトライ/バックオフと 5xx 判別を実装し、最終的に macro_sentiment が取得できない場合は 0.0 をフェールセーフとして使用
    - score_regime(conn, target_date, api_key=None): DB 書き込みはトランザクションで冪等（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス対策（date < target_date 等、内部で date.today() を直接参照しない）
- データプラットフォーム関連 (src/kabusys/data/)
  - ETL パイプラインインターフェース (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラス実装（取得数・保存数・品質問題・エラー等を集約、to_dict を提供）
    - 差分更新・バックフィル設計、品質チェックとの連携設計（quality モジュールを参照）
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar ベースの営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバック
    - calendar_update_job(conn, lookahead_days=90): J-Quants API からの差分取得・バックフィル・健全性チェック（未来日付の異常検出）と保存ロジック
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS) による安全策
  - jquants_client 統合（参照実装を利用する想定）と save / fetch の呼び出し箇所を用意
- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None）
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損時は None）
    - DuckDB 上の SQL を多用して効率的に計算
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。horizons のバリデーションあり
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（3 件未満で None）
    - rank: 同順位は平均ランクで処理（丸めで ties 検出を安定化）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
  - research パッケージのエクスポートを整備（zscore_normalize の再エクスポート含む）
- テスト・運用性向上
  - OpenAI 呼び出しなど外部依存部分はパッチ可能な内部関数として切り出し、unittest.mock による差し替えを想定
  - API キーは引数で注入可能（api_key パラメータ）でテストが容易
  - 多くの外部呼び出しでフェイルセーフ（失敗時に例外を投げずにスキップして続行）を採用

Changed
- N/A（初期リリースのため該当なし）

Fixed
- N/A（初期リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: 日次処理は内部で datetime.today()/date.today() を直接参照しない。target_date を明示的に受け取り、DB クエリにも date < target_date / date = target_date といった排他条件を使う設計。
- 冪等性: ETL / スコア保存 / calendar 更新等、DB 書き込みは可能な限り冪等に設計（DELETE→INSERT / ON CONFLICT 等）。
- フェイルセーフ: LLM 呼び出し失敗や API エラーはデフォルト値（0.0）やスキップで継続し、部分障害が全体停止を引き起こさないようにしている。
- DuckDB を主要な分析 DB として使用。executemany の空リストバインド問題など DuckDB の実装差分に配慮した実装を行っている。

今後の TODO（想定）
- strategy / execution / monitoring パッケージの実装拡充（現状はパッケージエクスポートのみ）
- jquants_client の具体的実装・テスト、外部 API のモック整備
- Windows 等環境依存ケースの .env パーシング追加テスト
- 単体テストおよび統合テストの追加（特に LLM 呼び出しのリトライ／パース回り）
- ドキュメント（Usage examples、API リファレンス）の整備

---