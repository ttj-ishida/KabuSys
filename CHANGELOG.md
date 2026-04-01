# CHANGELOG

すべての重要な変更点を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-01

### Added
- 初回リリース。日本株自動売買プラットフォーム「KabuSys」のコアモジュールを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン "0.1.0" とサブパッケージの公開（data, strategy, execution, monitoring）を定義。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを実装（プロジェクトルート検出に .git / pyproject.toml を利用）。
  - 自動ロード順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式やシングル／ダブルクォート、エスケープ、インラインコメントなどを考慮した堅牢な .env パーサを実装。
  - 既存 OS 環境変数を保護する protected オプション付きの上書き挙動を実装。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）などの取得とバリデーションを実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py）
  - raw_news / news_symbols を入力に、OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメントスコアリング機能を実装（score_news）。
  - タイムウィンドウ（前日15:00 JST〜当日08:30 JST 相当）計算（calc_news_window）。
  - バッチ処理（1回最大20銘柄）、1銘柄あたり記事数・文字数制限、JSON Mode を用いた堅牢なレスポンス検証およびスコアクリッピング（±1.0）。
  - 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフでのリトライロジック。
  - DB への冪等的書き込み（DELETE → INSERT）で部分失敗時に既存データを保護。
  - テスト用に OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能に設計）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）判定を実装（score_regime）。
  - マクロ記事抽出のためのキーワード集合／最大取得記事数・JSON レスポンスパース・API リトライ等を実装。
  - レジームスコア合成・閾値判定・market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - API 失敗時のフェイルセーフ（macro_sentiment=0.0）やログ出力を実装。
  - ルックアヘッドバイアスを避けるため、target_date 未満のデータのみを参照する等の設計方針に従う。

- リサーチ／ファクター処理（src/kabusys/research/）
  - factor_research.py
    - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）などの定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials を利用し、(date, code) ベースの結果を返す設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク相関）を用いた IC 計算、欠損や同順位（ties）への対処を実装。
  - research パッケージの __all__ を整備して主要関数を再エクスポート。

- データ基盤（src/kabusys/data/）
  - calendar_management.py
    - JPX マーケットカレンダーの管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といったユーティリティを提供。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・健全性チェック（将来日付の異常検知）・冪等保存をサポート。
    - DB にカレンダー情報がない場合は曜日ベースでフォールバックする挙動を明確に実装。
  - pipeline.py / etl.py
    - ETL パイプライン用の ETLResult データクラスを定義（etl モジュールから再エクスポート）。
    - 差分更新・バックフィル・品質チェックを行う設計方針とユーティリティ関数を実装（jquants_client / quality モジュールとの連携想定）。
    - ETLResult により実行結果・品質問題・エラー一覧を構造化して返却可能。

### Internal / Implementation notes
- DuckDB を主要なローカルデータストアとして想定し、SQL ウィンドウ関数や executemany を活用してパフォーマンスと互換性を考慮。
- 日付/時刻の取り扱いに厳格（全て date/naive UTC データを前提にし、target_date ベースでルックアヘッドを防止）。
- OpenAI との統合は JSON Mode（response_format={"type": "json_object"}）を想定し、JSON パースエラー時の復元処理や追加安全策を導入。
- 外部 API 依存時はフェイルセーフ（API 失敗でスコア 0 またはスキップ）を採用し、全体処理を停止させない設計。
- テスト容易性を考慮し、OpenAI 呼び出し部分や .env 自動ロードをテスト時に差し替え／無効化可能に設計。

### Known / TODO
- ETL パイプライン関連は設計が整っており主要構造は実装済みだが、周辺ユーティリティ（jquants_client, quality 等）との結合・運用検証が引き続き必要。
- ドキュメント（StrategyModel.md / DataPlatform.md 等）参照に依存する実装が多く、実運用前に外部ドキュメントとの整合性確認が推奨される。

--------------------------------------------
今後のリリースでは、発注（execution）やモニタリング機能、ストラテジ管理 UI、追加の品質検査ルール等の機能拡張を予定しています。