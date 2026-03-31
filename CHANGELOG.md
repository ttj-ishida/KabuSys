# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 以下はリポジトリ内のソースコードから機能・設計の意図を推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - 日本株自動売買／リサーチ／データ基盤向けライブラリ群。
  - パッケージメタ: src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサは以下をサポート:
    - export KEY=val 形式
    - シングル／ダブルクォートとバックスラッシュエスケープ
    - インラインコメントの扱い（クォート内は無視、非クォートでは '#' の直前が空白/タブのときにコメントと判断）
  - Settings クラスを提供（settings インスタンスを公開）。必須環境変数取得時は未設定で ValueError を送出。
    - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパス設定: DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
    - 環境種別の検証: KABUSYS_ENV は development / paper_trading / live のいずれかのみ許容
    - ログレベル検証: LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容

- ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメント評価を実行。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（ルックアヘッドバイアス防止）。
  - バッチ処理: 最大 20 銘柄／API 呼び出し、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ（最大回数制御）。
  - レスポンス検証: JSON の抽出、"results" 配列、各要素の code/score 検証、未知のコードは無視、スコアは ±1.0 にクリップ。
  - 書き込み: ai_scores テーブルへは取得済みコードのみを対象に DELETE -> INSERT（トランザクション）して置換。部分失敗で既存データを保護。
  - テスト容易性: OpenAI 呼び出しは _call_openai_api を patch して差し替え可能。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次の市場レジーム ('bull' / 'neutral' / 'bear') を判定。
  - マクロニュース抽出はニュースタイトルのキーワードマッチ（複数キーワード定義）で行う。
  - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得。API失敗時は 0.0 として継続（フォールトトレランス）。
  - スコア合成・クリップ後に market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT）。
  - テスト容易性: _call_openai_api を patch 可能。

- データ / カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルを用いた営業日判定とユーティリティを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB 登録がない場合は曜日（土日）ベースでフォールバック。DB 登録ありは DB 優先、未登録日は曜日フォールバックで一貫性を確保。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックあり。
  - 探索上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。

- ETL パイプラインとユーティリティ (kabusys.data.pipeline / kabusys.data.etl)
  - ETLResult データクラスを公開（ETL の実行結果、品質問題・エラー一覧を保持）。
  - 差分更新・バックフィル・品質チェックの設計方針に基づく実装（jquants_client / quality モジュールと連携想定）。
  - DuckDB 利用前提のヘルパー関数（最大日付取得・テーブル存在チェックなど）を実装。

- リサーチ／ファクター計算 (kabusys.research)
  - ファクター計算モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - calc_value: PER / ROE（raw_financials を参照）
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率
  - 特徴量探索モジュール:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算、ホライズン検証あり
    - calc_ic: スピアマンランク相関（IC）計算（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median の計算
    - rank: 平均ランク処理（丸めで ties を安定化）
  - いずれも DuckDB・SQL を主に利用し外部ライブラリ非依存で実装。ルックアヘッドバイアスを避ける設計。

### Changed
- （初期リリースのためなし）

### Fixed
- （初期リリースのためなし）

### Security
- OpenAI API キーは関数引数で注入可能（テストやキー管理の柔軟化）。環境変数未設定時は ValueError を発生させることで誤動作を防止。

---

補足メモ（実装上の注意点）
- 多くの処理でルックアヘッドバイアス回避のために date / target_date を外部引数で与え、date.today()/datetime.today() を直接参照しない設計。
- DuckDB を前提とした SQL 実装のため、executemany に空リストを渡さない等の互換性配慮がなされている（DuckDB 0.10 対応）。
- OpenAI 呼び出し（news_nlp / regime_detector）は JSON Mode を利用し、レスポンスの頑健なパース・検証へ配慮。
- トランザクション（BEGIN/COMMIT/ROLLBACK）を使用した冪等書き込みを多用し、部分失敗時のデータ保護を重視。

もし他にリリースノートに含めたい項目（例: 実際の変更日、著者、リリース手順、既知の制約など）があれば教えてください。必要に応じて項目を追加・修正します。