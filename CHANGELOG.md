# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルは、コードベース（kabusys）から推測される初期リリースの変更点を日本語でまとめたものです。

全般:
- 初期バージョンを公開（バージョン: 0.1.0）。
- パッケージメタ情報: src/kabusys/__init__.py にて __version__="0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- 環境設定管理
  - .env/.env.local ファイルおよび環境変数から設定を読み込む自動初期化機構を実装（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック：__file__ から親ディレクトリを探索し .git または pyproject.toml を基準にルートを特定。ルートが見つからない場合は自動ロードをスキップ。
  - .env パーサを実装：コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応する堅牢なパース処理を提供。
  - .env 読み込み優先順位：OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
  - Settings クラスに各種プロパティを提供（J-Quants, kabuステーション API, Slack, DBパス, 環境・ログレベル判定など）。未設定の必須変数は ValueError を送出。

- AI（自然言語処理）モジュール
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎に -1.0〜1.0 のスコアを生成。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST の UTC 換算）を計算するユーティリティ calc_news_window を提供。
    - API 呼び出しのバッチ処理（最大 20 銘柄/チャンク）、トークン膨張対策（1銘柄あたりの記事数と文字数上限）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードのみ DELETE→INSERT）など堅牢性を確保。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（モジュール内 private を patch 可能）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window によるウィンドウで抽出し、OpenAI（gpt-4o-mini）に投げて JSON を受け取り macro_sentiment を取得。
    - LLM 呼び出しはリトライ機構・フェイルセーフ（失敗時 macro_sentiment=0.0）を備える。
    - レジーム計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照しない設計。

- データ基盤（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理機能を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルが存在しない場合は曜日ベース（平日を営業日）でフォールバック。
    - DB 登録値を優先しつつ未登録日は曜日フォールバックで補完する一貫したロジック。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得・バックフィル・保存を行う。健全性チェック（未来日付過大時のスキップ）を実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新・保存・品質チェックを想定した ETLResult データクラスを実装。
    - ETL のユーティリティ関数（テーブル存在チェック・最大日付取得・市場カレンダー調整等）を実装。
    - jquants_client と quality モジュールとの連携を想定した設計。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に。

  - ETL の公開インターフェースとして ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）等の定量ファクターを DuckDB 上で計算する関数を追加（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 扱い、検索ウィンドウのバッファ設定などを実装。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API へはアクセスしない。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンに対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を内部で計算。
    - ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB で実装。

- モジュール構成
  - ai, data, research などのサブパッケージを整備。各モジュールはテスト時に差し替えやすいように内部呼び出し関数を設計（例: _call_openai_api を patch 可能）。

### 変更 (Changed)
- ロギングとエラーハンドリングを強化
  - API 失敗・DB 書き込み失敗時に詳細なログとフェイルセーフ挙動を導入。
  - DB トランザクションでの try/except による ROLLBACK 保護（さらに ROLLBACK 自体の失敗を警告ログ化）。

### 修正 (Fixed)
- N/A（初期リリースのため過去のバグ修正履歴はなし。実装中に考慮されたケースや注意点は各モジュールの docstring に明記）。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API キー未設定時は各スコア関数が ValueError を送出するため、運用環境では OPENAI_API_KEY または関数引数での注入が必要。
- news_nlp と regime_detector は LLM のレスポンスに強く依存するため、出力フォーマットの変化に対してはパースロジックの調整が必要。
- DuckDB の executemany に空リストを渡せない制約に対応するため、空リストチェックを導入している（互換性上の注意）。
- 日付計算は timezone-naive な date/datetime を使う方針で実装されており、UTC/JST の扱いについてはモジュール内コメントを参照のこと。

### セキュリティ (Security)
- 環境変数（API トークン等）が未設定の場合は明示的に例外を投げるため、誤った環境での実行を未然に防止。
- .env の自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストや CI 環境での漏洩リスク低減に寄与。

---

注記:
- 各機能の振る舞いや設計方針（ルックアヘッドバイアス回避、部分書込での安全性、LLM 呼び出しの冪等性/堅牢性、DuckDB の互換性配慮など）は各ソースファイルの docstring に詳細が書かれており、本CHANGELOGでは主要な追加点と設計上の重要事項を要約して記載しています。