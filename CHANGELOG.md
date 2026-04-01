# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定リリースはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-04-01

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。バージョン: 0.1.0。公開モジュール: data, strategy, execution, monitoring。

- 環境設定・自動 .env ロード
  - .env および .env.local ファイルの自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。CWD に依存しない設計。（src/kabusys/config.py）
  - .env 行パーサー: コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントに対応。
  - 読み込み時の上書き制御: OS 環境変数保護（protected set）、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスで各種設定プロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベル検証など）。必須環境変数未設定時は ValueError を送出。

- AI 関連
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - 記事ウィンドウ計算（JST ベースの前日 15:00 〜 当日 08:30 を UTC に変換）を提供する calc_news_window。
    - バッチサイズ制御、記事数／文字数トリム、最大リトライ（429/ネットワーク/タイムアウト/5xx 向け指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（書き込みは該当コードのみ削除→挿入）を実装。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（モックしやすい設計）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロ記事が存在しない、または API が失敗した場合は macro_sentiment = 0.0 とするフェイルセーフ。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける。リトライ・エラー種別ごとの取り扱いを明確化。

- データプラットフォーム（Data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定（is_trading_day）、前後営業日の取得（next_trading_day / prev_trading_day）、期間内営業日の列挙（get_trading_days）、SQ 日判定（is_sq_day）を実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィルと安全性チェックを含む）。
    - DB にデータがない/未登録日には曜日ベースのフォールバック（週末除外）を採用し、一貫した動作を保証。

  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得数／保存数／品質問題／エラー等の集約）。
    - 差分更新・バックフィル・品質チェックの設計方針とユーティリティ関数（テーブル存在チェック、最大日付取得等）を実装（ETL の骨格部分）。

- リサーチ（研究）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - Value: EPS/ROE から PER/ROE を算出（raw_financials から最新財務を参照）。
    - データ不足時の None 扱い、DuckDB を用いた SQL ベースの実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応・入力検証）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）とランク化ユーティリティ（rank）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの公開 API を整備（zscore_normalize の再利用など）。

- テスト・運用に配慮した設計上の注記（コード内設計方針）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を関数内部で直接参照しない。
  - DuckDB とトランザクション（BEGIN/DELETE/INSERT/COMMIT / ROLLBACK）の冪等書き込みとエラーハンドリングを採用。
  - OpenAI 呼び出しについては JSON パースの耐性強化（余計な前後テキストの復元）、数値変換と型チェック、未知コードの無視などの堅牢化を実装。
  - 外部 API エラーは基本的にフェイルセーフ（影響範囲を限定して継続）とし、部分失敗時に既存データを保護する実装方針。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

注記:
- 上記は現行コードベース（src/ 以下）から推測して作成した CHANGELOG です。実際のリリースノート作成時は、コミット履歴・実際の公開日・互換性ポリシー等を合わせて調整してください。