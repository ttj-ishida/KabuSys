# Changelog

すべての重要な変更をここに記載します。本ファイルは Keep a Changelog の形式に従っています。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」のコア機能セットを追加しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - モジュール群をパブリッシュ（data, strategy, execution, monitoring を __all__ で公開の意図）。

- 環境設定/ロード
  - 環境設定管理モジュールを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - .env パーサーはシングル/ダブルクォート、バックスラッシュエスケープ、行頭の export、行内コメント（空白直前の #）などに対応。
    - OS 環境変数を保護するための protected 機構（.env.local の上書き時にも保護）。
    - Settings クラスを提供し、必須環境変数取得（_require）のラッパーを実装。
    - デフォルト値を持つ設定：KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄毎にテキストを作成し、OpenAI（gpt-4o-mini）で一括センチメント評価。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / リクエスト）と 1 銘柄あたりのトリム（最大記事数／最大文字数）対応。
    - OpenAI JSON Mode を用いた厳密な JSON レスポンス想定と、レスポンスの堅牢なバリデーション（JSON の抽出・results 検査・コード/スコア検証・数値クリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフリトライ（最大試行回数制御）。
    - フェイルセーフ: API 呼び出し失敗時は個別チャンクをスキップし、部分成功の結果のみ ai_scores テーブルへ差し替え（DELETE → INSERT を個別実行して部分失敗時の既存データ保護）。
    - テスト容易化のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - score_news(conn, target_date, api_key=None) がパブリック API。成功時は書き込み銘柄数を返す。

  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（キーワードリストを実装）。
    - OpenAI（gpt-4o-mini）を用いた macro_sentiment 評価（JSON レスポンス想定）。
    - API エラー時は macro_sentiment を 0.0 とするフェイルセーフ。リトライ戦略を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) がパブリック API。成功時は 1 を返す。

- データ基盤（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定 API を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日を非営業日とする）。
    - next/prev/get_trading_days は DB 値優先かつ未登録日は曜日ベースで一貫した結果を返す。
    - calendar_update_job による夜間バッチ更新を実装（J-Quants から差分取得 → 保存）。バックフィル日数と健全性チェックを実装。
    - 最大探索日数・ルックアヘッド等の定数化（安全策）。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行のメタ情報（取得数・保存数・品質問題・エラー）を集約。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - 差分更新・バックフィル・品質チェックを行う設計方針をコードコメントに明記。
    - etl モジュールは ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）算出関数を実装。
    - DuckDB を用いた SQL 実装で、prices_daily / raw_financials のみを参照。外部 API にはアクセスしない設計。
    - 各関数は (date, code) をキーとした dict のリストを返す。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランキングユーティリティ（rank）、統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結。
  - research パッケージは主要関数を __all__ で再エクスポート。

- データユーティリティ
  - calc_news_window、その他日付ウィンドウ計算ユーティリティを追加。
  - 一部ユーティリティ（zscore_normalize）を再エクスポート（src/kabusys/research/__init__.py）。

### 変更 (Changed)
- （初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- （初回リリースのため修正履歴はありません）

### セキュリティ (Security)
- 外部 API（OpenAI / J-Quants）キーは引数経由または環境変数（OPENAI_API_KEY 等）で注入し、未設定時は明示的に ValueError を返す実装で安全性を考慮。

### 設計上の注意・挙動
- ルックアヘッドバイアス対策
  - ニューススコアリング・レジーム判定・ファクター計算等のアルゴリズムは内部で datetime.today()/date.today() を直接参照しないように設計されており、必ず caller が target_date を渡す方式でルックアヘッドを防止しています（一部バッチジョブで date.today() を使う箇所あり、意図が明記されています）。
- フェイルセーフ
  - OpenAI 呼び出しや外部 API の失敗は、サービス全体を止めないように部分スキップ・デフォルト値（例: macro_sentiment=0.0）で継続する設計。
- DB 書き込みの冪等性
  - calendar_update_job、score_regime、score_news などは既存データの上書き（DELETE→INSERT や ON CONFLICT）を明確に行い、部分失敗時に既存データを不必要に消さない配慮あり。
- テスト容易性
  - OpenAI 呼び出し層は内部関数を patch 可能にしてあり、ユニットテストの差し替えを想定。

---

注記: 本 CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際のリリースノートと差異がある場合があります。