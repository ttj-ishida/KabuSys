Keep a Changelog に準拠した CHANGELOG.md

全般:
- この CHANGELOG はリポジトリ内の現在のコードから推測して作成しています。実際のコミット履歴ではなく、初期リリース（v0.1.0）で導入された主要な機能・設計上の注意点をまとめています。

Unreleased
- （なし）

0.1.0 - 2026-04-01
Added
- 初回リリース: KabuSys — 日本株自動売買／データ分析プラットフォームの基礎モジュール群を導入。
  - パッケージ公開情報
    - src/kabusys/__init__.py によるパッケージエクスポート（data, strategy, execution, monitoring）。
    - バージョン: 0.1.0

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local からの自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env パーサーは export 形式／引用符／エスケープ／インラインコメントの取り扱いに対応。
    - OS 環境変数を protected として優先する読み込みロジック（override / protected オプション）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを取得（必須設定は未設定時に ValueError を送出）。
    - デフォルト値、型変換（float, Path 等）、値検証（有効な env 値・ログレベル）を実装。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメント解析を実装。OpenAI（gpt-4o-mini, JSON mode）を用いて銘柄ごとに -1.0〜1.0 のスコアを生成し、ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）の計算（calc_news_window）。
    - 銘柄ごとに記事を集約（最大記事数・文字数でトリム）、最大バッチ数でチャンク送信（_BATCH_SIZE=20）。
    - レート制限／ネットワーク断／タイムアウト／5xx に対する指数バックオフリトライを実装。失敗時は個別チャンクをスキップして継続（フェイルセーフ）。
    - API レスポンスの厳格なバリデーションとスコアクリップ（±1.0）。部分成功時は対象コードのみ置換（DELETE → INSERT）、部分失敗で他の既存スコアを保護。
    - DuckDB executemany の制約（空リストは不可）を考慮した実装。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定（bull / neutral / bear）機能を導入。
    - 日次で ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジームスコアを算出。
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini, JSON mode）。記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 にフォールバック。
    - API 呼び出しのリトライ/エラーハンドリング（RateLimit / ネットワーク / タイムアウト / 5xx の再試行）。パース失敗時は 0.0 にフォールバック。
    - DuckDB への冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外を再送出。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/pipeline.py, etl.py, calendar_management.py
    - ETL パイプライン用の基盤（ETLResult データクラスの導入、差分取得・保存・品質チェックの設計方針を実装）。
    - ETLResult は取得件数・保存件数・品質検出結果・エラー情報を保持し、has_errors / has_quality_errors / to_dict を提供。
    - market_calendar の管理（calendar_update_job）:
      - J-Quants API からの差分取得、バックフィル（直近 _BACKFILL_DAYS の再取得）、健全性チェック（未来日異常検出）を実装。
      - market_calendar の有無に応じたフォールバック（DB 未登録日は曜日ベースの判定）。
    - 営業日関連ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。DB の登録値優先かつ未登録日は曜日フォールバックで一貫した結果を返す。
      - 最大探索範囲制限（_MAX_SEARCH_DAYS）により無限ループを防止。
    - jquants_client 経由の保存処理に対する例外捕捉とログ出力。

- リサーチ（Research）モジュール
  - src/kabusys/research/factor_research.py, feature_exploration.py
    - ファクター計算:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を prices_daily から計算。データ不足時は None を返す仕様。
      - calc_volatility: 20 日 ATR / 相対 ATR / 20 日平均売買代金 / 出来高比率を計算。true_range の NULL 伝播に注意した設計（不完全データでの誤検出回避）。
      - calc_value: raw_financials から直近の財務数値を取得し PER / ROE を計算（EPS が 0 または NULL の場合は PER = None）。
    - 特徴量探索:
      - calc_forward_returns: 与えられた horizon リストに対する将来リターンを一度の SQL で取得。horizons の検証（正の整数, <=252）。
      - calc_ic: スピアマンのランク相関（IC）を実装。十分なレコードがない場合は None。
      - rank, factor_summary: 同順位は平均ランク、統計サマリー（count/mean/std/min/max/median）を純粋 Python（外部依存なし）で実装。
    - 設計方針として DuckDB 接続のみを参照し、本番取引 API へはアクセスしない安全性を維持。

- 共通設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアスの防止:
    - AI / リサーチ等の多くの関数は内部で datetime.today() / date.today() を参照せず、必ず外部から target_date を受け取る設計。
    - DB クエリは target_date 未満を用いるなどルックアヘッドを避ける条件を明示。
  - フェイルセーフ設計:
    - OpenAI 呼び出しや外部 API の失敗時は基本的にスコアを中立（0.0）にフォールバックする、または該当チャンクをスキップして処理継続する挙動を採用。
  - DuckDB 互換性考慮:
    - executemany に空リストを渡せないバージョンへの対応（事前チェック）や date 型変換ユーティリティを実装。
  - DB 書き込みは冪等（DELETE → INSERT 等、トランザクションで囲む）を目指す。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記（Known notes / 想定される運用上の注意）
- OpenAI API の利用:
  - API キーは score_news / score_regime の api_key 引数または環境変数 OPENAI_API_KEY で提供。未設定時は ValueError を送出して処理を終了します。
  - 使用モデルは gpt-4o-mini（JSON Mode）を想定しており、レスポンスの JSON パース・バリデーションを厳格に行いますが、LLM の出力が期待通りでない場合はその銘柄／チャンクをスキップする動作になります。
- .env パーシングは一般的なケース（export, quoted values, inline comments）に対応していますが、極端に複雑なシェル式は想定外の挙動になる可能性があります。
- DuckDB のバージョン差分（executemany の挙動や配列バインドの互換性）に依存する箇所はコード内で注記・回避策がとられていますが、実運用前に使用する DuckDB バージョンでの動作確認を推奨します。
- calendar_update_job は J-Quants クライアント（jquants_client）実装に依存します。API の変更やレスポンス不具合に対しては例外処理とログ出力でフェイルセーフ化しています。

補足
- 実コードには strategy / execution / monitoring モジュール名でのエクスポートが定義されていますが、今回提示された抜粋にそれらの具体実装は含まれていません。これらはフレームワーク層として将来的に取引ロジック・発注・監視機能を提供する想定です。

（終）