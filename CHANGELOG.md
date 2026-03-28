# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム "KabuSys" のコアライブラリを提供します。以下の主要コンポーネントと機能を含みます。

### 追加
- 基本パッケージ情報
  - パッケージ名: kabusys
  - __version__ = 0.1.0
  - パッケージの公開 API（__all__）に data / strategy / execution / monitoring を含む（将来の拡張ポイント）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定をロードする自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env / .env.local の読み込み順序と保護（OS環境変数の保護）に対応。
  - export KEY=val 形式やクォート、インラインコメントなどの .env 文法を考慮したパーサーを実装。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 実行環境（development/paper_trading/live） / ログレベル等の取得とバリデーションを行うプロパティを実装。
  - env, log_level の検証（許容値チェック）を実装。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - OpenAI（gpt-4o-mini）を使ったニュースの銘柄別センチメント解析機能。
    - ニュースの時間ウィンドウ計算（JST基準）と記事集約（銘柄ごとに記事をトリムして結合）を実装。
    - バッチ送信（最大 20 銘柄/回）、JSON mode を利用したレスポンス処理、レスポンスバリデーション、スコアクリッピング（±1.0）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - AI スコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易化のため _call_openai_api を patch 可能に実装。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - prices_daily, raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロニュース抽出と OpenAI 呼び出し（リトライ・フェイルセーフ）を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY で供給可能。
    - LLM 呼び出し回りはモジュール間でプライベート関数を共有しない設計（結合度低減）。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを一貫して適用。
    - カレンダー更新バッチ（calendar_update_job）: J-Quants API から差分取得 → 冪等保存、バックフィル、健全性チェックを実装。
  - ETL / pipeline
    - ETL 実行結果を表す ETLResult データクラスを公開（ETL の取得・保存件数、品質問題、エラーを集約）。
    - 差分取得・保存・品質チェックを行うパイプラインの土台を実装。J-Quants client 経由でデータを取得・保存する設計。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどユーティリティを実装。
    - DuckDB の executemany に関する互換性を考慮した実装（空リスト送信の回避）。

- Research モジュール（kabusys.research）
  - factor_research
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20日 ATR、ATR比率、20日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: PER / ROE を raw_financials と prices_daily から計算する calc_value を実装。
    - DuckDB のウィンドウ関数・集計を用いた効率的な実装。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC（Spearman ランク相関）計算 calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
  - zscore_normalize を kabusys.data.stats から再エクスポート。

### 変更（設計上の重要事項・挙動）
- ルックアヘッドバイアス防止設計
  - AI スコア算出やレジーム判定、ファクター計算等の関数は内部で datetime.today() / date.today() を参照せず、必ず caller が与える target_date を基準に動作する。
  - DB クエリは target_date 未満または target_date に対するリード/ラグ指定でルックアヘッドを防止。

- フェイルセーフ方針
  - LLM/API 呼び出しの失敗時は例外を投げずフェイルセーフなデフォルト値（例: macro_sentiment=0.0、スコア取得失敗はスキップ）で継続する部分が多く、システム全体の堅牢性を重視。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK が失敗した場合は警告ログを出力。

- テスト容易性
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）を patch 可能に設計し、ユニットテストで API 呼び出しを差し替えられる。

- DuckDB 互換性
  - DuckDB 0.10 系での executemany の挙動（空リスト不可）を考慮して空パラメータリストを送らない実装になっている。

### 修正（バグ修正や注意点）
- 環境変数パーサーでのクォート・エスケープ文字処理に対応し、.env 内の複雑な文字列も安全に読み込めるように改善。
- ニュースやマクロキーワード抽出において SQL の LIKE 条件を ILIKE（大文字小文字無視）で実行するように実装。

### 破壊的変更（注意）
- Settings.env / log_level の値検証で不正値は ValueError を発生させるため、既存の環境変数値が許容値外の場合はアプリケーション起動時に失敗します。KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか、LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかにしてください。
- news_nlp.score_news と regime_detector.score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が未設定だと ValueError を投げます。呼び出し側でキーを供給してください。

### 既知の制限 / 今後の改善点
- strategy / execution / monitoring パッケージは __all__ に含まれているが、このリリースでは実装ファイルが含まれていないか限定的（将来のリリースで注文実行ロジックや監視機能を追加予定）。
- AI モデル依存: 現在は gpt-4o-mini を想定したプロンプトと JSON mode を利用。将来的なモデル変更や API 仕様変更に伴う調整が必要になる可能性あり。
- ニューステキストのトリムや最大記事数は固定定数（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）で決まっているため、銘柄ごとに要調整になる可能性あり。

---

今後のリリースでは、実際の注文実行コンポーネント、監視/アラート機能、より多様なファクター・最適化処理、そして外部 API のエラー観測性向上（メトリクス等）を計画しています。