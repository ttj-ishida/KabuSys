# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠します。  
初版リリース: 0.1.0

## [0.1.0] - 2026-03-27

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。
  - バージョン: `__version__ = "0.1.0"`。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ に定義）。

- 環境設定（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env パーサ実装
    - export KEY=val 形式対応、シングル/ダブルクォート対応（バックスラッシュエスケープを考慮）、行末コメント処理。
    - 無効行（空行、コメント行、等）は無視。
  - 上書き挙動制御
    - .env.local は既存 OS 環境変数を protected として保持しつつ上書き可能（.env は未設定キーのみ設定）。
  - Settings クラスを提供（settings インスタンス）
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティを公開。
    - env / log_level の値検証（許容値チェック）。
    - is_live / is_paper / is_dev の補助プロパティ。

- AI（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部で UTC に変換）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数/文字数上限を設定（肥大化対策）。
    - JSON mode を利用した厳格なレスポンスパースとバリデーション実装（結果検証: keys/type/既知コード/数値）。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - フェイルセーフ: API 失敗やパース失敗時は対象銘柄をスキップして処理継続（例外を投げない設計）。  
    - DuckDB の executemany の制約（空リスト不可）を回避するため事前チェックを実施。
    - テスト用フック: `_call_openai_api` を patch して差し替え可能。
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を算出・保存。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロキーワードで記事を抽出し、OpenAI によるセンチメント算出（記事が無ければ LLM 呼び出しをスキップし macro_sentiment=0.0）。
    - API エラー時はフォールバックして継続（macro_sentiment=0.0）。
    - DB 操作は冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - テスト用フック: `_call_openai_api` は news_nlp 実装と独立しており、モジュール結合を避ける設計。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 最大探索日数の上限を設定して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存（冪等）を行う夜間バッチ実装。健全性チェックあり（過度に未来日付のスキップ等）。
  - ETL パイプライン（pipeline）
    - 差分取得 → 保存 → 品質チェック のワークフロー設計。
    - ETL 実行結果を表す ETLResult dataclass を追加（品質問題やエラーの収集・集約機能、to_dict メソッド）。
    - 最終取得日の自動算出、backfill 日数設定、品質チェックは呼び出し元で判断できるようなエラー収集型設計（Fail-Fast ではない）。
    - DuckDB の日付最大取得ユーティリティなどを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: PER、ROE を raw_financials と prices_daily から計算。
    - 設計方針として DuckDB による SQL ベース実装、ルックアヘッド回避、欠損値処理。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons に対する入力検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足時は None を返す。
    - factor_summary: 各ファクターの基本統計（count/mean/std/min/max/median）を計算。
    - rank: ランク付け（同順位は平均ランク）。
  - data.stats.zscore_normalize を再エクスポート。

### Changed
- 設計・実装上の多くの箇所で「ルックアヘッドバイアス防止」の方針を徹底。
  - datetime.today() / date.today() による暗黙的時刻参照を避け、target_date を明示して処理する設計。
- OpenAI 呼び出しに対する堅牢化（リトライ、5xx 判定、JSON パース回復処理、ログ出力）。
- DuckDB 周りの互換性考慮:
  - executemany に空リストを渡さないガード、list 型バインドの回避策（個別 DELETE を用いる）など。

### Fixed
- （初期リリースのため該当無し）  

### Security
- 環境変数の取り扱い強化:
  - .env 読み込み時に OS 環境変数を保護する機構を実装（protected set）。
  - 必須キー未設定時は明示的に ValueError を発生させて早期検出。

### Notes / Implementation details
- すべての外部 API 呼び出し（OpenAI / J-Quants）は、API キーを引数で注入可能にすることでテスト容易性を確保（api_key 引数を受け取る）。
- 多くの関数は DuckDB 接続オブジェクトを引数に取り、テスト時にインメモリ DB を差し替え可能。
- OpenAI に対するテスト用フックとして内部の _call_openai_api を patch して外部呼び出しを模擬可能。
- DB 書き込みは部分失敗時に既存データを不必要に消さないよう、書き込み対象コードを絞って DELETE → INSERT を行う実装。

---
今後の予定（例）
- strategy / execution / monitoring の実装拡充（本リリースでは基礎部のみ公開）。
- ドキュメント整備、ユニットテストの追加、CI/CD パイプラインの導入。