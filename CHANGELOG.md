CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はコミット時点の想定日を使用しています。

フォーマットの概要:
- 各バージョンは [バージョン] - 日付 の形式で記載
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security を使用

[Unreleased]
-----------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開用の __version__ と __all__ を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途を想定）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理）。
  - .env ファイル読み込みでの上書き制御（override, protected）をサポートし、OS 環境変数を保護。
  - Settings クラスを提供。J-Quants / kabu API / Slack / DB パス等の設定プロパティを公開し、必須項目は未設定時に ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST に対応する UTC の範囲計算機能（calc_news_window）。
    - バッチ処理（最大20銘柄/回）、1銘柄あたり最大記事数・最大文字数のトリム、JSON Mode による厳密なレスポンス期待。
    - API リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスのバリデーション・スコアクリッピング（±1.0）・部分成功時の DB の保護（スコア取得済みコードのみ置換）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事抽出のためのキーワードリスト、上限記事数、OpenAI 呼び出し（gpt-4o-mini）とリトライ処理を実装。
    - レジームスコアのクリップ・閾値判定および market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。

- Data モジュール (kabusys.data)
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックを行う一貫した実装。
    - カレンダー夜間更新ジョブ (calendar_update_job)：J-Quants から差分取得し冪等保存、バックフィル、健全性チェックを実装。
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー情報等を保持）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映したユーティリティを実装（内部関数: _get_max_date, _table_exists など）。
    - jquants_client との連携想定点を確保（fetch/save の呼び出しを想定した構成）。
  - jquants_client のラッパー呼び出しポイントを想定（実体は外部モジュールに委任）。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None ハンドリング、性能を意識したスキャン日数のバッファリング。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部ライブラリに依存しない純粋 Python 実装（DuckDB のみ依存）。
  - 研究系ユーティリティの再エクスポート（zscore_normalize 等）。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- なし

Removed
- なし

Security
- API キーはメソッド引数で注入可能（api_key 引数を受け付ける関数が多数）で、環境変数依存を緩和。  
  ※ セキュリティ上の注意: OpenAI や外部 API キーは管理下に置くこと。

Notes / 設計上の注記
- ルックアヘッドバイアス対策:
  - 各種処理（ニューススコア・レジーム判定・ETL・研究処理）は datetime.today() や date.today() を内部参照せず、外部から target_date を受け取る設計。
  - DB クエリでは date < target_date / date BETWEEN … などの排他条件で将来データの使用を防止。
- フェイルセーフ設計:
  - OpenAI API の一時エラーやレスポンスパース失敗時は例外を上位に投げず、安全側のデフォルト値（0.0 やスキップ）で継続する実装が多く含まれる。
- DuckDB を主要なデータストアとして想定。executemany の空リスト問題等（DuckDB 0.10 の制約）に配慮した実装が含まれる。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数をモック差し替え可能にしている（例: _call_openai_api の patch）。

今後の予定（想定）
- jquants_client / kabu API の具体的実装との統合テスト
- 監視・実行（execution / monitoring）モジュールの実装（__all__ にプレースホルダあり）
- ドキュメント充実（使用例、DB スキーマ、運用手順）

お問い合わせ
- 問い合わせやバグ報告はリポジトリの Issue をご利用ください。