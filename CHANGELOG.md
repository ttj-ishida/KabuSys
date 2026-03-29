# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基本設定
  - パッケージルート: `kabusys`、バージョン `0.1.0` を宣言（src/kabusys/__init__.py）。
  - 公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ による整理）。

- 環境変数／設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート（.git または pyproject.toml を検出）を起点に .env を検索（CWD に依存しない挙動）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env のパース機能を強化（コメント、export 形式、シングル/ダブルクォート・エスケープ、インラインコメントの取り扱い等に対応）。
  - 環境変数取得のユーティリティ `_require` と型付き Settings クラスを提供。
    - J-Quants / kabu ステーション / Slack / DB パス / ログレベル / 実行環境（development/paper_trading/live）のプロパティを提供。
    - env と log_level の検証ロジックを実装（無効値は ValueError）。
    - デフォルトの DB パスや API ベース URL の既定値を設定。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを統合して OpenAI（gpt-4o-mini + JSON mode）へ送信してセンチメントスコアを算出。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数のトリム、結果のバリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - API エラーやパース失敗はフェイルセーフでスキップし、partial write を避けるために取得できた銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）する設計。
    - テスト容易性のため、内部の OpenAI 呼び出し関数を差し替え可能にしている。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)（JST基準のウィンドウをUTC naive datetimeで返す）
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（タイトルベース、マクロキーワードリスト）→ OpenAI（gpt-4o-mini）で JSON レスポンスを期待してセンチメント抽出。
    - API 呼び出しのリトライ・エラーハンドリング（RateLimit, Connection, Timeout, APIError）を実装。API 失敗時は macro_sentiment=0.0 のフォールバック。
    - DuckDB 経由で ma200_ratio を計算し、結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT を使用）。
    - 公開関数: score_regime(conn, target_date, api_key=None)
  - 共通設計上の配慮
    - LLM 呼び出しは各モジュールで独立実装（内部プライベート関数は共有しない）し、ユニットテストで容易にモック可能。

- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを管理する market_calendar テーブル向けのユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などの判定関数を提供。DB に登録がない場合は曜日ベースでフォールバック（週末除外）。
    - カレンダー更新バッチ job: calendar_update_job(conn, lookahead_days=90) を実装（J-Quants クライアント経由で差分取得 → 保存、バックフィル、健全性チェック）。
    - 最大探索日数の上限やバックフィル日数、異常時のスキップなど安全措置を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETL の実行結果を表すデータクラス ETLResult を実装（取得・保存件数、品質問題、エラー等を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）などの設計方針を実装方針として明示。
    - 汎用ユーティリティ（テーブル存在チェック、最大日付取得、トレーディングデイ補正等）を提供。
  - ETL の公開インターフェースを再エクスポート（src/kabusys/data/etl.py: ETLResult）。

- リサーチ・ファクター（src/kabusys/research）
  - factor_research.py
    - モメンタム、バリュー、ボラティリティ／流動性の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）計算。データ不足時は None を扱う。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高変化率を計算。
    - calc_value: latest 財務データ（raw_financials）と当日の株価を用いた PER/ROE の計算（EPS が 0 または欠損なら None）。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。ホライズン検証と効率的な1クエリ取得を実装。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（None や ties に対する処理を含む）。
    - rank: 同順位は平均ランクを割り当てるランク変換（丸めによる ties の検出ロバスト化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。
  - 研究用ユーティリティをパッケージで公開（src/kabusys/research/__init__.py にて関数を再エクスポート）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の読み込みで OS 環境変数を保護する仕組みを導入（.env 読み込み時に既存の OS 環境変数を上書きしない、ただし .env.local は override を許可するが保護キーセットを考慮）。
- OpenAI API キーの未設定時は明示的なエラーを投げる（誤った無音失敗を防止）。

### 設計上の注意点 / 既知の挙動
- ルックアヘッドバイアス防止のため、日付計算やクエリは内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- DuckDB を主要なストレージとして利用。executemany に対する互換性考慮（空リスト投入の回避等）。
- LLM 呼び出しは JSON Mode を想定し、レスポンスのパース失敗時はログ出力してフェイルセーフで継続する。
- テストしやすいように内部 API 呼び出し関数（_call_openai_api 等）をモック可能にしている。
- 部分失敗時に既存データを保護するため、書き込みは対象コードを限定した DELETE → INSERT の方式を採用。

---

将来的なリリースでは、監視・実行（execution/monitoring）、戦略（strategy）周りの実装拡張、より詳細な品質チェックとマイグレーションツール、CI/CD やドキュメントの整備を予定しています。