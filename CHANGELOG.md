# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0 — 2026-04-04

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システムのコアライブラリを公開します。主に以下の機能群を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - public API 想定のモジュール一覧を __all__ で定義（data, strategy, execution, monitoring。未実装モジュールは将来拡張想定）。

- 環境設定・.env ローディング (src/kabusys/config.py)
  - .env / .env.local からの自動環境変数読み込みを実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - export KEY=val 形式やクォート／エスケープ、コメント扱い（#）に対応したパーサ実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 設定アクセス用 Settings クラスを提供。J-Quants / kabu API / LINE / DB パス /監視閾値・システム設定などのプロパティを公開。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須変数取得時のエラー (_require)。

- データ処理 / ETL (src/kabusys/data/)
  - ETL パイプライン結果を表す ETLResult を公開（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
  - DuckDB を用いた ETL 実装方針とユーティリティを実装（テーブル存在チェック・最大日付取得等のユーティリティが含まれる）。
  - 市場カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定ユーティリティ。
    - J-Quants からの夜間バッチ更新 job (calendar_update_job) を実装。DB優先、未登録日は曜日ベースでフォールバック。
    - バックフィルや健全性チェックを備え、冪等保存を想定（J-Quants クライアント経由の fetch/save を呼ぶ）。

- 研究（Research）機能 (src/kabusys/research/)
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200日MA乖離 (calc_momentum)。
    - ボラティリティ / 流動性: 20日 ATR、相対ATR、20日平均売買代金、出来高比率 (calc_volatility)。
    - バリュー: PER, ROE（raw_financials と prices_daily 組合せ）(calc_value)。
    - DuckDB を利用し、prices_daily / raw_financials のみ参照、外部発注等には依存しない設計。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）。
    - IC（Information Coefficient）計算（Spearman の ρ）(calc_ic)。
    - ランク変換ユーティリティ (rank)。
    - ファクター統計サマリー (factor_summary)。
  - research パッケージの公開 API を整理 (__init__.py)。

- AI / ニュースNLP（OpenAI 統合） (src/kabusys/ai/)
  - ニュースセンチメント計測モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini を用いたセンチメントスコアを生成して ai_scores テーブルへ保存。
    - 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（銘柄ごとに最大20銘柄 / チャンク）、1 銘柄あたりのトークン肥大化対策（記事数・文字数制限）。
    - レスポンスのバリデーションと数値クリップ、部分書き込み（取得できたコードのみ DELETE→INSERT）で部分失敗耐性を確保。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するリトライ/指数バックオフ。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - DuckDB からの価格・ニュース取得、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント算出、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - LLM 呼び出しもテスト用差し替えポイントあり。

- データユーティリティ
  - jquants_client など外部依存クライアントを想定した抽象化（calendar / pipeline から利用）。
  - DuckDB を中心とした SQL 主導の実装により、外部ライブラリ（pandas 等）に依存しない実装方針。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 実装方針・安全設計
- ルックアヘッドバイアス回避:
  - 全ての分析／スコア関数は内部で datetime.today() / date.today() を参照しない設計。外部から target_date を明示して与える形を採用。
  - DB クエリは target_date より前または半開区間等で明示的にフィルタしている。
- DB 操作の冪等性:
  - market_regime / ai_scores などのテーブル書き込みは DELETE→INSERT などで冪等性を担保。トランザクション（BEGIN/COMMIT/ROLLBACK）を使用。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時はスコアに 0.0 を代入して処理継続する等、致命的停止を避ける挙動を多く取り入れている（ログ出力あり）。
- テスト容易性:
  - OpenAI 呼び出し部分は _call_openai_api を patch してモック可能。API キー注入（引数経由）もサポート。
- 環境変数の優先順位:
  - OS 環境変数を保護しつつ .env/.env.local を自動読み込み（.env.local は上書き）。既存 OS 環境変数は protected として上書き回避。

### 既知の制限 / 今後の改善候補
- strategy / execution / monitoring などの実行／監視周りの実装はパッケージ公開時点では限定的（インターフェースは定義されているが詳細は今後追加予定）。
- ai モジュールは gpt-4o-mini と JSON Mode を前提に実装しているため、OpenAI SDK やモデル仕様の変更があった場合に追加調整が必要。
- DuckDB の executemany に空リストを渡せない制約への対応（コード内で明示的にチェック）を行っているが、将来的に DB バージョン差異対応の拡充が望ましい。

---

今後のリリースでは、strategy（売買ロジック）や execution（発注処理）、monitoring（稼働監視・アラート）の実装強化、テストカバレッジの拡張、ドキュメント整備を行う予定です。詳細な変更履歴は次バージョンで追記します。