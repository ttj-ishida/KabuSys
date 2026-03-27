Keep a Changelog 準拠の CHANGELOG.md（日本語）
===========================================

全般
----
- フォーマット: Keep a Changelog に準拠
- このファイルは、コードベースから推定した初期リリースの変更点・機能一覧をまとめたものです。
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせて記載しています。

Unreleased
----------
（現在のところ未リリースの変更はありません）

0.1.0 - 初期公開リリース (2026-03-27)
-----------------------------------
追加 (Added)
- 基本情報
  - パッケージ名: kabusys
  - エクスポートされるサブパッケージ: data, strategy, execution, monitoring

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込み順: OS 環境変数 > .env.local > .env
    - パッケージ配布後も正しく動作するよう、__file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索。
    - 自動読み込みを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env のパースは堅牢に実装（export プレフィックス対応、シングル/ダブルクォートとエスケープの取り扱い、インラインコメントの扱い等）。
  - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得可能。
    - 必須値を未設定で参照した場合は ValueError を送出。
    - 設定検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG..CRITICAL） の検証
    - DB パス取得（DUCKDB_PATH / SQLITE_PATH のデフォルトを提供）
  - OS 環境変数の上書きを防ぐための protected キーセットを使用した .env 上書きロジック。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を扱う calc_news_window を提供（UTC で比較する実装）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄ずつ API に送信、1 銘柄あたりトリム（記事数・文字数）してプロンプト肥大を防止。
    - 再試行/フォールバック:
      - 429 (RateLimit), ネットワーク断, タイムアウト, 5xx サーバーエラーに対して指数バックオフでリトライ。
      - API 失敗やパース失敗は例外にせず該当チャンクをスキップ（フェイルセーフ）。
    - レスポンス検証: JSON 抽出・検証（results 配列の存在、各要素の code/score、数値性、既知コードのみ採用）、スコアを ±1.0 にクリップ。
    - 書き込みはトランザクションで行い、部分失敗時に既存データを削らないよう code を絞って DELETE→INSERT を実行（DuckDB の executemany 空リスト制約に配慮）。
    - テスト容易性: OpenAI 呼び出しポイント（_call_openai_api）をパッチ置換可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド回避）。
    - マクロニュースは news_nlp.calc_news_window を用いて窓を決め、キーワードフィルタでタイトルを抽出。
    - OpenAI 呼び出しは gpt-4o-mini を JSON mode で使い、リトライと 5xx と非 5xx を区別した挙動を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時は ROLLBACK を試みる。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から直近の財務データを取得し PER / ROE を計算（EPS=0/欠損は None）。PBR・配当利回りは未実装。
    - 実装方針: DuckDB 上の SQL + Python で完結し本番取引 API にはアクセスしない。
  - feature_exploration モジュール
    - calc_forward_returns: 指定株価から将来リターン（任意ホライズン）を一括クエリで取得（horizons のバリデーションあり）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算、有効レコードが 3 未満で None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、統計サマリ（count/mean/std/min/max/median）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API を用いた差分取得・バックフィル・健全性チェック（未来日付の異常検出）・冪等保存（jquants_client 経由）。
    - 最大探索日数やバックフィル日数（デフォルト）を定数で定義し無限ループ防止を考慮。
  - pipeline / ETL
    - ETLResult dataclass を公開（etl モジュールを通じて再エクスポート）。
    - 差分取得、保存、品質チェック（quality モジュール）を想定した設計。
    - _get_max_date 等のユーティリティを実装し、テーブル未作成/空テーブルへの対応を行う。

- データベース/互換性
  - DuckDB を主要なストレージとして使用。
  - DuckDB の executemany に対する空リスト制約などの互換性問題に配慮した実装。

変更 (Changed)
- 該当なし（初期リリース）

修正 (Fixed)
- 該当なし（初期リリース）

削除 (Removed)
- 該当なし（初期リリース）

既知の制限・注意点
- 一部のファクター（PBR・配当利回り）は未実装。
- データ不足時のフォールバックはログ出力のうえ中立値（例: ma200_ratio=1.0）や None を返す実装がある。
- OpenAI のレスポンスが期待フォーマットでない場合はスキップして継続するため、部分的にスコアが欠落することがある。
- OpenAI 呼び出しの振る舞いは SDK の将来変更に影響を受ける可能性がある（status_code の取り扱い等は getattr で安全化）。
- テスト容易性のために API 呼び出し関数を差し替え可能にしている（unittest.mock.patch を想定）。

設計上の重要ポイント
- ルックアヘッドバイアス防止: 各種スコアリング/計算は datetime.today()/date.today() を直接参照しない（target_date を明示的に渡す設計）。
- フェイルセーフ: 外部 API エラーは完全停止させず、部分的にフォールバックして処理を継続する方針。
- トランザクション管理: DB 書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）で保護し、ROLLBACK failure を警告ログに記録。
- テスト性: API キー注入や _call_openai_api のパッチ可能化など、ユニットテストを考慮した実装になっている。

補足
- 実際のリリース日や追加のバージョンは、今後の変更に応じて本 CHANGELOG を更新してください。