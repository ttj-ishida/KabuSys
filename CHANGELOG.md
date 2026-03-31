CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従っています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys。トップレベル公開: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を提供（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）をプロパティ経由で厳密に取得・検証。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄毎に記事を結合し、OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリング。
    - バッチサイズ、記事数・文字数のトリム制限、429/接続断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証（JSON パース、results フィールド、code/score 検証、数値チェック、スコア ±1.0 クリップ）。
    - DuckDB への書き込みは冪等（部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api をパッチ）。
    - ニュース収集ウィンドウ計算ユーティリティ calc_news_window を提供（JST の前日15:00 〜 当日08:30 を UTC に変換）。

  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で regime_label（bull/neutral/bear）を算出。
    - OpenAI API 呼び出しのリトライ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - レジームスコアは閾値でラベリングし、スコアは -1.0〜1.0 にクリップ。

- データプラットフォーム / ETL (src/kabusys/data)
  - calendar_management
    - JPX カレンダー管理（market_calendar）。営業日判定・前後営業日取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録有無や NULL 値時の曜日ベースフォールバック、最大探索日数の制限、夜間バッチ更新ジョブ calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック）を提供。
    - market_calendar が未取得の場合も安全に動作する設計。
  - pipeline / ETLResult
    - ETLResult dataclass を公開（ETL 実行結果・品質問題・エラーを集約）。
    - 差分更新・バックフィル・品質チェックを踏まえた ETL 設計を想定するユーティリティ群。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS 欠損 → PER は None）。
    - すべて DuckDB と prices_daily / raw_financials テーブルを参照する純粋分析関数として実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）で将来リターンを計算。入力チェックあり（horizons は 1〜252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（欠損や同値処理に対応、3 銘柄未満で None）。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸め処理で ties の誤検出を防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- その他
  - DuckDB を中心としたデータ設計（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブルを前提）。
  - OpenAI の SDK を利用（OpenAI クライアント生成を内部で行うが、API キーは引数で注入可能）。
  - テスト容易化のため、OpenAI 呼び出しを差し替え可能な設計（ユニットテストでのモックを想定）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 設計・実装上の注意点 / 既知の制約
- 時刻/日付取り扱い
  - ニュースウィンドウは JST ベースで定義され、内部処理では UTC-naive な datetime を利用（DB 側の datetime は UTC 保存を前提）。
  - 計算関数は datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。target_date を明示的に渡す必要がある。
- フェイルセーフ
  - LLM 呼び出しの失敗は例外を潰して 0.0（中立）にフォールバックする箇所がある（news/regime の一部）。運用での監視ログ確認が必要。
- DuckDB 互換性
  - DuckDB のバージョン差異（executemany の空リストバインド等）に配慮したコードが含まれるが、実行環境の DuckDB バージョンに依存する可能性あり。
- OpenAI SDK 依存
  - OpenAI のレスポンス形式や SDK の例外クラスに依存している（status_code の有無など）。将来の SDK 変更に対する互換性注意。

### マイグレーション / 実行上のメモ
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API を使う場合）
- .env 自動ロードはプロジェクトルートの検出に基づく（.git または pyproject.toml が存在するディレクトリ）。CI/コンテナ環境で .env を使う場合は配置を確認。
- 自動 .env 読み込みを抑止したいテストなどは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

---

貢献者: コードベースから推定してドキュメント化。実際のリリース時には日付・貢献者情報を更新してください。