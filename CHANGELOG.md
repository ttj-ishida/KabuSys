# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョンはパッケージ内定義に合わせて 0.1.0 です。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加機能と設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開モジュール群を定義（data, strategy, execution, monitoring）。
  - パッケージバージョン定義: __version__ = "0.1.0"。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により CWD に依存しない読み込みを実現。
  - .env パーサ実装（export プレフィックス対応・クォート／エスケープ処理・インラインコメント処理など）。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で停止可能。
  - Settings クラスを提供し、必要な環境変数をプロパティとして取得（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル等）。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と便利なブールプロパティ（is_live, is_paper, is_dev）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST の定義と UTC での比較処理（calc_news_window）。
    - バッチサイズ、文字数・記事数上限、JSON Mode（厳密な JSON 期待）などのトークン肥大化対策。
    - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーションとスコアの ±1.0 クリップを実装。
    - 得られたスコアを ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。部分失敗時に既存スコアを保護する実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しは独立実装で、APIキーの注入可能性あり。API失敗時は macro_sentiment=0.0 のフォールバック。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定ユーティリティを提供。DB 登録優先、未登録日は曜日ベースでフォールバック。
    - 最大探索範囲やバックフィル、健全性チェック等を組み込み（探索上限・バックフィル日数・将来日検査）。

  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを公開し、ETL 実行結果（取得件数、保存件数、品質問題、エラー一覧など）を構造化。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計（詳細は pipeline モジュールに準拠）。
    - jquants_client 経由の保存は冪等（ON CONFLICT DO UPDATE）を想定。

- リサーチツール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の計算関数を提供。
    - DuckDB を用いた SQL + Python 実装。結果は (date, code) をキーとする dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純標準ライブラリ実装を志向。
  - data.stats からの zscore_normalize を再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- OpenAI コール周りや DB 書き込み失敗発生時の堅牢性処理を実装
  - LLM 呼び出しの例外分類に基づくリトライ戦略（RateLimitError / APIConnectionError / APITimeoutError / APIError の扱い）を追加。
  - JSON パース失敗や無効レスポンス時はログ出力のうえスキップまたはフォールバックして例外を投げない方針を採用（フェイルセーフ）。

### 既知の制限 (Known issues)
- OpenAI API キーは事前に環境変数 OPENAI_API_KEY または関数引数で与える必要がある（未設定時は ValueError を送出）。
- DuckDB に依存する SQL バインド挙動（executemany の空リスト不可など）に配慮した実装をしているが、古い DuckDB バージョンでは一部動作が異なる可能性がある。
- news_nlp / regime_detector といった LLM 連携部は外部 API に依存するため、API 料金や利用制限に留意が必要。

### セキュリティ (Security)
- 特段のセキュリティ修正は含まれていません。環境変数や API キーの取り扱いは OS 環境変数をプロテクトする実装（config の protected set）で配慮していますが、本番運用時はシークレット管理（Vault 等）を推奨します。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・PR 説明等に基づいた確認を推奨します。