CHANGELOG
=========

全般
-----
このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0 を公開。
  - 概要: 日本株自動売買システムのコアライブラリ群を提供。データ取得/ETL、マーケットカレンダー管理、ファクター計算（リサーチ）、ニュース NLP、レジーム判定、設定管理などの機能を含む。

- 環境設定・読み込み (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート判定を __file__ を起点に .git または pyproject.toml で行うため、CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化が可能（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォート無しの場合のインラインコメント判定（直前が空白/タブならコメント扱い）
  - Settings クラスを提供（環境変数経由で各種設定を取得）
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル 等のプロパティを定義
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値セットをチェック）
    - パス系は Path に変換し expanduser を適用

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None): raw_news + news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとにセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（calc_news_window）: JST 基準で「前日 15:00 〜 当日 08:30」を UTC naive datetime に変換して DB クエリに使用。
  - バッチ処理: 最大 20 銘柄/回 (_BATCH_SIZE)、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - 再試行とフォールバック:
    - RateLimit / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（最大回数設定あり）。
    - API 呼び出し失敗時は該当チャンクをスキップして残りを継続（フェイルセーフ）。
  - レスポンス検証:
    - JSON パース、"results" リスト、code と score の存在などを検証。不整合は無視して安全に継続。
    - 数値チェックと ±1.0 でクリップ。
    - JSON mode で前後に余計なテキストが混入したケースは最外側の {} を抽出して復元を試みる保守的な処理あり。
  - DB 書き込みは冪等操作（DELETE で該当 code を消してから INSERT）を行い、部分失敗時に他のコードの既存スコアを保持する設計。

- レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ保存。
  - ma200_ratio 計算: target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立(1.0)にフォールバック。
  - マクロニュース抽出: raw_news から国内/グローバルのマクロキーワードでフィルタ（最大記事数制限）。
  - OpenAI 呼び出しは独立実装で例外・再試行処理を備え、API 失敗時は macro_sentiment=0.0 として継続。
  - レジームスコアのクリップと閾値に基づくラベリング（'bull' / 'neutral' / 'bear'）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を保ち、失敗時は ROLLBACK（失敗ログ）を試行。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の際は曜日ベース（土日非営業日）のフォールバックロジックを採用。
    - DB 登録日を優先し、未登録日の扱いは曜日フォールバックで一貫性を保持。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分フェッチして market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を導入し ETL 実行結果（取得件数・保存件数・品質チェックの問題・エラー一覧）を表現。
    - 差分更新、バックフィル、品質チェック（quality モジュール経由）を想定した設計。ETL の品質問題は集約して報告し、呼び出し元が対応を決定可能。
    - data.etl モジュールで ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev（200 日 MA に対する乖離率）を計算。データ不足銘柄は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。データ不足で None を返す設計。
    - calc_value(conn, target_date): raw_financials から最新財務（report_date <= target_date）を取得して PER / ROE を計算。EPS が 0 または欠損なら PER は None。
    - 設計方針: DuckDB の SQL 構造を活用し、外部 API にはアクセスしない（リサーチ環境で安全に実行）。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 複数ホライズンの将来リターンをまとめて取得する効率的な SQL 実装。horizons の検証（正の整数かつ <=252）あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（Information Coefficient）を算出。有効レコードが 3 件未満の場合は None を返す。
    - rank(values): 同順位は平均ランクを返す実装（丸めで ties 検出漏れを防止）。
    - factor_summary(records, columns): 各ファクター列の count/mean/std/min/max/median を計算。
    - 外部依存を極力排し、標準ライブラリのみで実装。

- 汎用・実装上の考慮点
  - DuckDB をデータ層として利用する設計（関数は DuckDB 接続を受け取る）。
  - ルックアヘッドバイアス回避: date.today()/datetime.today() を内部ロジックで参照しない設計（API 呼び出し側が target_date を渡す）。
  - API 呼び出し周りは詳細な再試行・ログ出力・フォールバック方針を持ち、運用時の堅牢性を重視。
  - DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、冪等性を確保するために DELETE→INSERT 等を使用。
  - テスト容易性のため OpenAI 呼び出し箇所は内部関数を patch して差し替え可能に設計（ユニットテスト向けの注記あり）。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- （現時点で報告されたセキュリティ修正は無し）

補足（実装上の注意）
- OpenAI API キー未設定時は明示的に ValueError を送出する箇所がある（score_news / score_regime）。
- .env の自動ロードは OS 環境変数を保護する仕組み（protected set）を実装しており .env.local で OS 環境変数を上書き可能。
- DuckDB の executemany はバージョン依存で空リストを受け付けない制約を考慮した実装パターンが用いられている（空の params の際は呼ばない）。

今後のタスク（候補）
- ドキュメント（API リファレンス・実行例）の充実
- テストカバレッジの拡張（特に OpenAI まわりのモックテスト）
- jquants_client / kabu API クライアントの実装と統合テスト
- 運用向けのモニタリング・アラート設定（LINE 通知等の活用）

上記はコードベースからの推測に基づく変更点／機能説明です。実際のリリースノート作成時はリポジトリのコミットメッセージやリリースタグに基づいて調整してください。