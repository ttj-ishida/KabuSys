CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。
このファイルは "Keep a Changelog" の慣習に準拠しています。
なお、本リリースノートは提供されたコードベースから実装内容を推測して作成しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

初回リリース。日本株向けのデータプラットフォーム／リサーチ／AI支援を備えた自動売買補助ライブラリを提供します。
主要な追加機能と動作仕様は以下の通りです。

Added
- 基本パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ = "0.1.0"。
  - パブリックモジュールとして data, strategy, execution, monitoring を公開。

- 環境設定モジュール（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート探索は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートのエスケープ処理、インラインコメント処理などに対応。
  - 環境変数保護:
    - OS 環境変数を protected として .env ファイルによる上書きを避ける機能を実装。
  - Settings クラスを提供（settings インスタンス経由で取得）。
    - J-Quants、kabuステーション、LINE、DB（duckdb/sqlite）パス、監視閾値等のプロパティを実装。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - 各種閾値・パスはデフォルト値を持つ。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから対象記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - 1 銘柄あたりの最大記事数・最大文字数でトリム（トークン肥大対策）。
    - 最大バッチサイズ 20 銘柄／コール、JSON Mode を利用して厳密な JSON レスポンスを想定。
    - リトライポリシー: 429・接続断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出・results フィールド検証・数値変換・未知コード無視・±1.0 クリップ。
    - 成功分のみ ai_scores テーブルを置換（部分失敗時に他銘柄の既存スコアを保護するためコード絞り込み DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None) -> 書き込み銘柄数。
    - calc_news_window(target_date) を公開（テスト可能なウィンドウ計算）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して
      日次で market_regime テーブルへ書き込み（'bull'/'neutral'/'bear'）。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュース取得は news_nlp.calc_news_window に基づき raw_news からマクロキーワードでフィルタ。
    - OpenAI 呼び出しは JSON モードで実行し、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。例外時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None) -> 1（成功）。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA に対する乖離）を計算。データ不足時は None。
    - calc_volatility(conn, target_date): atr_20、atr_pct、avg_turnover、volume_ratio を計算。ATR は true_range の NULL 伝播を適切に制御。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER/ROE を計算（EPS が 0/欠損時は None）。
    - 実装方針: DuckDB 上で SQL と Python を組み合わせ、外部 API にアクセスしない。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関により IC を計算。データ不足（<3）なら None。
    - rank(values): 同順位は平均ランクで処理（浮動小数誤差対策の丸めを採用）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出。
  - research パッケージは zscore_normalize をデータユーティリティから再利用。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の全てで
      market_calendar の DB 登録値を優先し、未登録日は曜日ベース（週末を休場）でフォールバック。
    - next/prev_trading_day は探索上限（_MAX_SEARCH_DAYS=60）を設けて無限ループを防止。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して market_calendar を更新（バックフィルや健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を追加（target_date, fetched/saved counts, quality_issues, errors を保持）。
    - 差分更新・バックフィル・品質チェックの設計方針に準拠する実装方針をコード中に明記。
    - _table_exists / _get_max_date 等のユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させる設計で安全性を考慮。

Notes / 注意事項
- ルックアヘッドバイアス防止: 主要な日次処理（news ウィンドウ計算、MA 計算、レジーム判定、score_news 等）は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える設計です。テスト／バッチ実行時に過去日を指定して再現可能。
- DuckDB に対する executemany の互換性（空リスト不可）を考慮した実装が含まれます（ai_scores など）。
- OpenAI 呼び出し周りは JSON Mode を使ったレスポンスパースと冗長性・リトライ制御を持ち、API 失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続する設計です。
- .env パースは Bash 風の軽量な互換処理を行いますが、複雑なシェル拡張には対応しません。例: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの限定的な処理。

Acknowledgements / 依存
- DuckDB をデータ保存／分析向けに利用する想定。
- OpenAI Python SDK を用いた LLM 呼び出し（gpt-4o-mini, JSON Mode）を利用。
- J-Quants API クライアント（kabusys.data.jquants_client として参照）および kabuステーション API との連携を想定。
- 実行環境により追加依存が発生する可能性があります（例: openai ライブラリのバージョン差分に伴う APIError/status_code の取り扱い等）。

今後の予定（例）
- strategy / execution / monitoring の詳細実装とドキュメント化。
- テストカバレッジ拡充（特に OpenAI 呼び出しのモックパス）。
- パフォーマンス最適化（DuckDB クエリのインデックス、バッチサイズの自動調整など）。

---
この CHANGELOG は初期実装に基づく推測記述を含みます。実際のリリースノート作成時にはコミットログや PR 説明と突合して確定してください。