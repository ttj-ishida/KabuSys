# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、SemVer を想定しています。

## [Unreleased]

（現在のコードベースは初回公開バージョンに相当します。次回リリース前にここへ追記してください。）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株のデータプラットフォーム、リサーチ、AIを組み合わせた自動売買／リサーチ基盤の骨格を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは __version__ = "0.1.0"。
  - パッケージ公開インターフェースとして data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env のパースは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント等に対応。
  - 環境変数必須チェック用の helper (_require) と Settings クラスを提供。デフォルト値や検証（KABUSYS_ENV, LOG_LEVEL 等の許容値）を含む。
  - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を Settings で提供。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へ送信してセンチメントスコアを取得する機能を実装。
    - calc_news_window によるニュース収集ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1 銘柄あたり記事数上限、文字数トリム等のトークン肥大化対策を実装。
    - JSON Mode を前提にレスポンス検証ロジックを実装（厳格な検証、未知コード無視、スコア ±1 にクリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時は部分スキップ（フェイルセーフ）。
    - ai_scores テーブルへは「該当コードのみ」DELETE → INSERT することで冪等性と部分失敗時の保護を実現。
    - テスト容易性のため _call_openai_api を patch 可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70% 重み）とマクロセンチメント（30% 重み）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から ma200_ratio を算出し、raw_news のマクロキーワードに一致するタイトルを抽出して LLM に送信。
    - OpenAI 呼び出しにリトライ・フェイルセーフ処理を実装。API 失敗時は macro_sentiment=0.0 として継続。
    - 結果は market_regime テーブルに冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
    - ルックアヘッドバイアス防止（date 未満のデータのみ参照、datetime.today() を直接参照しない）を設計指針に明示。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日（平日）ベースのフォールバックを実装。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・保存（fetch_market_calendar / save_market_calendar を使用）をサポート。健全性チェックやバックフィルの実装あり。
    - 最大探索日数 (_MAX_SEARCH_DAYS) 等の安全ガードを追加。

  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを公開（target_date、各種取得／保存件数、quality_issues、errors 等）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）、jquants_client 経由の idempotent 保存を想定した設計を文書化。
    - DuckDB の互換性考慮（テーブル存在チェック、MAX(date) 取得、executemany の空リスト回避等）を取り入れたユーティリティを実装。

  - jquants_client 経由のデータ取得と保存（クライアント連携の契約点を想定）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL ウィンドウ関数を利用する実装で、外部 API や実取引 API にはアクセスしない。
    - データ不足時には None を返す方針。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic）計算、rank、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI の API キーは関数引数で注入可能（api_key）、無ければ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させ、誤操作を防止。

### Design / Implementation Notes（重要な設計判断）
- ルックアヘッドバイアス対策: 日次処理は常に target_date を明示的に受け取り、データ取得は target_date 未満／以前という排他的条件を利用。
- フェイルセーフ: 外部 API 失敗時に処理を停止せずフォールバック（スコア 0.0 や記事スキップ）して継続する方針。
- 冪等性: DB への書き込みは部分失敗で既存データを不意に消さないよう、コード単位で削除 → 挿入する方針を採用。
- テスト容易性: OpenAI 呼び出し等を内部関数でラップし、テスト時に patch できる設計にしてある。
- DuckDB 互換性: executemany に空リストを渡さないなど、DuckDB バージョン差異に配慮した実装。

---

今後の予定（例）
- strategy / execution モジュールの実装（実際の発注ロジック・バックテスト接続）。
- 監視（monitoring）と Slack 通知統合の実装・拡充。
- テストカバレッジの強化と CI/CD パイプライン整備。

---

参照
- 本CHANGELOGはコードの注釈・docstring に基づいて作成しました。実際のリリース時には変更点に応じて日付・バージョンを更新してください。