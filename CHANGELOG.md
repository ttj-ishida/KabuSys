# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムの基礎ライブラリを追加します。主要な機能・モジュールは以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ定義と公開 API（kabusys.__init__）。バージョン 0.1.0。
  - モジュール群: data, research, ai, execution, strategy, monitoring（公開名として __all__ に定義）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどを考慮した堅牢なパース実装。
  - 上書き制御: .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）。OS 環境変数を protected として .env.local の上書きから保護。
  - Settings クラス: 各種必須/任意設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
  - 入力検証: KABUSYS_ENV と LOG_LEVEL の有効値チェック、未設定必須値での明確なエラーメッセージを実装。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等に安全なデフォルトを設定。

- データ（Data Platform）モジュール
  - calendar_management:
    - JPX カレンダー管理。market_calendar テーブルに基づく営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した振る舞い。
    - 夜間バッチ更新 job: calendar_update_job を実装（J-Quants API から差分取得 → 保存、バックフィル、健全性チェック）。
    - _MAX_SEARCH_DAYS 等の探索制限により無限ループを防止。
  - pipeline / etl:
    - ETL 基盤 (kabusys.data.pipeline): 差分取得・保存・品質チェックの設計を実装。
    - ETLResult データクラスを追加（結果サマリ、品質問題・エラーの保持、辞書化ユーティリティ）。
    - jquants_client 経由での取得・保存処理および backfill の概念を導入。
  - etl モジュール: ETLResult を再エクスポート。

- AI（自然言語処理）モジュール
  - news_nlp:
    - raw_news と news_symbols を用いた銘柄別ニュース集約。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - 1 銘柄当たり記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（バッチサイズ上限、JSON mode 利用）。
    - 再試行戦略（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時はスキップ継続）。
    - レスポンス検証: JSON パース回復処理、results キーの検証、コード照合・数値検証、スコアの ±1.0 クリップ。
    - DuckDB 互換性配慮: executemany に空リストを与えないなどの実装。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、影響範囲を成功コードのみに限定）。
  - regime_detector:
    - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（ma200_ratio）計算。
    - マクロニュースの LLM センチメントを組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - 重み付け: MA (70%) / マクロセンチメント (30%)、スコア合成と閾値によるラベル判定。
    - OpenAI 呼び出しは独立実装、最大リトライ、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - ルックアヘッドバイアス回避のため date 比較や DB クエリは target_date 未満のデータのみを使用し、datetime.today()/date.today() を参照しない設計。

- リサーチ（Research）モジュール
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB を用いた SQL 中心の実装。prices_daily / raw_financials テーブルのみ参照し外部取引 API にアクセスしない安全設計。
    - データ不足時は None を返す等の堅牢なハンドリング。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターン計算（LEAD を利用）、horizons のバリデーション、パフォーマンス用のスキャン範囲制限。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（Information Coefficient）計算。
    - rank: 平均ランク（同順位は平均ランク）算出。丸めで ties を安定化。
    - factor_summary: count/mean/std/min/max/median の統計サマリ算出（None を除外）。
  - research パッケージ __all__ で主要関数を公開（zscore_normalize は data.stats から再利用）。

### 変更 (Changed)
- （初版のため履歴はなし）

### 修正 (Fixed)
- （初版のため履歴はなし）

### セキュリティ (Security)
- 環境変数の扱いに注意:
  - 必須トークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は Settings 経由で取得し、未設定時に ValueError を投げることで明確に扱う。
  - .env 読み込みは OS の環境変数を保護する挙動をデフォルトとする。

### 設計上の注意・備考
- ルックアヘッドバイアス防止: 多くの分析/判定コードは datetime.today()/date.today() を直接参照しない設計（外部から target_date を注入する）。
- テスト容易性: OpenAI 呼び出し関数（_call_openai_api）をパッチ可能にすることでユニットテストを容易にしている。
- DuckDB 互換性: executemany に空リストを渡すとエラーになるバージョンを考慮した安全実装を行っている。
- 外部 API への依存は明示的（jquants_client, OpenAI）。実運用では適切な API キー設定と接続確認が必要。

---

上記は現行コードベースの実装内容から推測して作成した CHANGELOG です。必要ならば個別機能ごとにより細かいサブ項目（例: ログメッセージ、定数名、戻り値仕様、エラー挙動の詳細）を追記できます。どの程度の粒度で変更履歴を残したいか教えてください。