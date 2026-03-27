# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従います。  
現在のバージョンは semantic versioning に従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - モジュールエクスポート: data, strategy, execution, monitoring

- 環境設定・自動読み込み
  - .env/.env.local ファイルと OS 環境変数から設定をロードする自動ローダを実装（プロジェクトルートは .git または pyproject.toml により探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（src/kabusys/config.py）。
  - .env パーサは以下をサポート:
    - 空行・コメント行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート外で直前が空白/タブの `#` をコメントとして扱う）
    - ファイル読み込み失敗時は警告を出して継続
  - Settings クラスに主要設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須キーチェック
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL のバリデーション
    - is_live/is_paper/is_dev の便利プロパティ

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング: news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）の JSON Mode で一括評価
    - API 呼び出しはチャンク単位（デフォルト 20 銘柄/回）
    - リトライポリシー（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）
    - レスポンス検証とスコアの ±1.0 クリップ
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）
    - テスト容易性のため OpenAI 呼び出し箇所をパッチ可能に実装（内部関数 _call_openai_api を patch 可能）
    - ニュースウィンドウ計算 calc_news_window（JST を基準とする UTC naive datetime の返却）

  - 市場レジーム判定: ai.regime_detector.score_regime
    - ETF 1321（日経225連動）200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
    - prices_daily からの MA 計算はルックアヘッドバイアスを防ぐため target_date 未満のデータのみを使用
    - マクロニュース抽出はタイトルベースでキーワード検索（最大記事数制限）
    - OpenAI 呼び出しは専用実装で分離、API 失敗時は macro_sentiment=0.0 で継続するフォールバック
    - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を実行してエラーを伝播

- データプラットフォーム（DuckDB ベース）
  - calendar_management モジュール
    - JPX カレンダー管理、祝日・半日取引・SQ日の判定／探索ユーティリティを実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等を提供
    - market_calendar がない場合は曜日ベース（土日除外）のフォールバックを使用
    - カレンダーデータの更新ジョブ calendar_update_job（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）を実装

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開し、ETL の取得数・保存数・品質問題・エラーの集約をサポート
    - 差分取得・backfill・保存（jquants_client の save_* を前提）・品質チェックの方針を整備
    - 内部ユーティリティ: テーブル存在確認、最大日付取得などを実装

- Research（ファクター計算・特徴量探索）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR（atr_20）、ATR 比率（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER（EPS が有効な場合）・ROE を計算
    - DuckDB SQL による実装、データ不足時の None 扱い、結果は辞書リストで返却
  - feature_exploration モジュール
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得する SQL 実装
    - calc_ic: スピアマンのランク相関（IC）を計算、3 銘柄未満は None を返す
    - rank: 同順位は平均ランクとして処理（小数丸め対策あり）
    - factor_summary: 各カラムの count/mean/std/min/max/median を返す（None 除外）
    - 外部ライブラリに依存せず純粋な標準実装

- ロギング・堅牢性
  - 多くの箇所でログ出力（info/debug/warning/exception）を実装
  - DB 操作での BEGIN/COMMIT/ROLLBACK によるトランザクション保護と、ROLLBACK 失敗時の警告ログ
  - 外部 API（OpenAI, J-Quants）呼び出しに対するリトライ・フォールバックロジックを整備
  - datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）を全 AI/スコアリング関数で徹底

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

---

開発上の注記・運用メモ:
- OpenAI API を利用する機能は api_key 引数で明示的にキーを渡せる。渡さない場合は環境変数 OPENAI_API_KEY を参照する（未設定時は ValueError）。
- DuckDB を主要なローカルデータストアとして利用する設計のため、ランタイム環境に DuckDB と OpenAI SDK（openai）が必要。
- .env の自動読み込みはパッケージの import 時に走るため、ユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして副作用を抑えることを推奨。

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴や実績テスト結果に基づく追記・修正を推奨します。）