# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコア機能群を実装・公開。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。バージョンは 0.1.0。
  - 公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ にて指定）。

- 設定 / 環境管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - export KEY=val 形式やクォート/エスケープ、インラインコメント処理に対応した .env パーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル等の取得を提供。未設定の必須環境変数は明示的にエラーを投げる。
  - DUCKDB / SQLITE のパス取得は Path オブジェクトで返却。

- AI: ニュース NLP (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ (calc_news_window) を提供。
  - バッチ処理（最大 20 銘柄／コール）、記事数・文字数制限（記事数上限・1銘柄あたり最大文字数トリム）によるトークン肥大化対策を実装。
  - OpenAI への呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーション（results 配列、コード整合性、数値チェック）を行う。
  - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ）を実装。API 失敗は個別チャンクをスキップしてフェイルセーフに処理を継続。
  - スコアは ±1.0 にクリップ。書き込みは部分失敗時に既存データを守るため、対象コードのみ DELETE → INSERT の置換を実行。
  - テスト容易性のため OpenAI 呼び出し用の内部関数をパッチ可能に設計。

- AI: 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する処理を実装。
  - マクロ記事抽出はニュースのタイトルに対するキーワードフィルタを使用。OpenAI（gpt-4o-mini）で macro_sentiment を評価し、複数回のリトライ・フォールバック（API 失敗時は 0.0）を実装。
  - レジームスコアはクリップされ、閾値によりラベル決定。結果は market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
  - ルックアヘッドバイアスを避ける設計（datetime.today() を参照しない、DB クエリは target_date 未満のデータのみを参照）。

- データ処理 / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX（市場）カレンダーの管理ロジックを実装（market_calendar テーブルの夜間バッチ更新ジョブ calendar_update_job を含む）。
  - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB 登録がない場合の曜日ベースのフォールバックや、DB 値優先の一貫した振る舞いを実装。最大探索日数の上限で無限ループを防止。
  - J-Quants クライアント経由で差分取得・冪等保存を行う仕組み（fetch/save 呼び出しの呼び出し・例外処理を含む）。

- データ ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装し ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化して返却可能に。
  - 差分更新、バックフィル、品質チェック（quality モジュール）を行う設計方針をドキュメント化（実装内に記載）。
  - DuckDB 上でのテーブル存在チェック、最大日付取得等のユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - ファクター計算モジュールを提供:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の None 処理）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: 最新財務データ（raw_financials）を用いて PER / ROE を計算。
  - 特徴量探索モジュールを提供:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - 実装は DuckDB と標準ライブラリのみを利用する方針で、外部依存を抑制。

- 共通・設計方針に関する注記
  - ルックアヘッドバイアス防止の徹底（datetime.today()/date.today() を使用しない設計方針の記載）。
  - DuckDB を利用した SQL + Python ハイブリッド実装。多くの書き込みは冪等化（DELETE → INSERT / ON CONFLICT 相当）を意識。
  - OpenAI 呼び出し部分は例外処理・リトライ・ログ出力に配慮し、テスト時は内部呼び出し関数をモック可能にしている。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

注: 実装は現時点で主要機能のロジック部分を中心に含みます。外部 API（J-Quants / OpenAI / kabu ステーション）との実運用や運用上のシークレット管理、監査ログ・監視の詳細設定は別途運用ルールに従ってください。