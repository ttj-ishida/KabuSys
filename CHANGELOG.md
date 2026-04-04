# Changelog

すべての重要な変更をこのファイルに記録します。  
このドキュメントは「Keep a Changelog」仕様に準拠しています。  

現在のリポジトリバージョンは src/kabusys/__version__ に合わせて 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース — 基本機能の実装を行いました。主に日本株自動売買プラットフォームの基盤となる以下のモジュールと機能を追加しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パブリックAPIとして data, strategy, execution, monitoring を __all__ に公開（パッケージ構造のエントリポイント）。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - 読み込みルール:
    - OS環境変数 > .env.local > .env の優先順位。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env のパースは export プレフィックス、クォート、インラインコメント、エスケープに対応。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB /監視 /システム関連の設定をプロパティ経由で取得。
  - 必須項目未設定時は _require() により ValueError を発生させる検証を追加。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を追加。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news, news_symbols を集約し、銘柄ごとにニュースをバッチで OpenAI（gpt-4o-mini）に送りセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST の記事）計算 util を提供（calc_news_window）。
    - バッチサイズ、文字上限、記事数上限の制御を実装(_BATCH_SIZE, _MAX_CHARS_PER_STOCK 等)。
    - API 呼び出しは JSON Mode を期待し、レスポンスのバリデーションと数値クリッピング（±1.0）を実装。
    - 429/ネットワーク断/タイムアウト/5xx エラーに対する指数バックオフリトライを実装。APIエラーはフェイルセーフ（失敗したチャンクはスキップ）。
    - DuckDB 互換性を考慮し、部分更新（対象 code の DELETE → INSERT）で冪等性を確保。executemany の空リストバインドを回避。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp のウィンドウヘルパを利用して取得し、独自の OpenAI 呼び出し実装でセンチメントを算出（news_nlp の内部関数を共有しない設計）。
    - API 呼び出しに対するリトライ/バックオフ/フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を参照しない方針を徹底（入力の target_date のみ参照）。

- データ処理 / ETL（kabusys.data）
  - ETLResult 型を提供（kabusys.data.pipeline。etl モジュールで再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック（quality モジュール）を組み合わせる設計骨格を実装。
    - ETL の結果を集約するデータクラス（ETLResult）を実装し、品質問題・エラー情報を保持して呼び出し元が判断できる構成。
    - DuckDB テーブル存在チェックや最終取得日の取得などのユーティリティを実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装：J-Quants クライアントから差分取得 → market_calendar へ冪等保存。
    - 営業日判定ユーティリティ群を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DBにカレンダーデータがない場合の曜日ベースのフォールバック、DB 値優先の一貫した判定、最大探索日数の上限を実装。
    - バックフィル／健全性チェック（将来日付の異常検出）を実装。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日 ATR）、Value（PER, ROE）等を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 入力は prices_daily / raw_financials に限定し、本番注文系APIにはアクセスしない設計。
    - 結果は date/code を含む dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを効率的に取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装し、必要レコード不足時は None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
  - research パッケージ __all__ に主要関数を公開（zscore_normalize は kabusys.data.stats からの再利用を想定）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- OpenAI API キーの取り扱いは env 経由で注入可能。API キー未設定時は ValueError を発生させて明示的に扱う設計。

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止: AI スコアリングやレジーム算出等の関数は内部で現在日時を自律参照せず、必ず外部から渡された target_date を基準として処理します。
- フェイルセーフ: 外部 API エラー・予期せぬレスポンスは基本的に局所的にフォールバック（スコア=0 等）して処理を継続します。これにより ETL や夜間バッチが一部の外部問題で中断されにくい設計です。
- 冪等性: DB への書き込みはできる限り冪等に実装（DELETE → INSERT、ON CONFLICT 相当）し、部分失敗時に既存データの損失を最小化するよう配慮しています。
- テスト容易性: OpenAI や時間依存処理の箇所は外部から差し替え（モック）可能な設計コメントや独立関数実装方針を採用しています（例: _call_openai_api の差し替え）。

---

今後の予定（例）
- strategy / execution / monitoring の詳細実装（order execution、監視・自動再起動、実口座との接続処理など）
- テストカバレッジの拡充（ユニット・統合テスト）
- ドキュメント（Usage、デプロイ、運用手順）の整備

(注) この CHANGELOG はソースコードからの推測に基づいて作成しています。詳細や実運用上の要件は実際のドキュメントや実装と照合してください。