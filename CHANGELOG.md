CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
バージョンは semantic versioning に従います。

Unreleased
----------
（なし）

0.1.0 - 2026-03-31
------------------
初回リリース。日本株自動売買システムのコアライブラリを実装しました。
主な追加点は以下の通りです。

Added
- パッケージ基盤
  - パッケージのメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート判定: .git / pyproject.toml）。
  - .env と .env.local の優先順位を実装（OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 複雑な .env パース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB / 監視 / システム設定をプロパティ経由で取得。必須値未設定時は ValueError を送出。
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）や LOG_LEVEL の検証を実装。

- AI サービス (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）にバッチ問い合わせして銘柄別センチメント（-1.0〜1.0）を算出する score_news を実装。
    - API リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、JSON レスポンスの堅牢なバリデーション（部分テキストの復元、未知コードの無視、数値変換チェック）を実装。
    - チャンク単位（デフォルト 20 銘柄）のバッチ送信、1 銘柄あたりの記事数と文字数のトリム制限を実装。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）を実装。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily からの MA 計算、raw_news のマクロキーワードフィルタ、OpenAI への問い合わせ、スコア合成、market_regime テーブルへの冪等書き込みを行う。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライ戦略、ログ出力を実装。
    - 内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス回避）。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルが不完全な場合は曜日ベースのフォールバックを行い、一貫性のある動作を保証。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（バックフィル／健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約する仕組みを提供。
    - 差分更新、バックフィル、品質チェックの骨格を実装（jquants_client と quality モジュールを呼び出す前提）。
    - data.etl モジュールで ETLResult を再エクスポート。
  - ユーティリティ
    - DuckDB の存在チェックや日付最大値取得などの内部ユーティリティを実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム（1m/3m/6m リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）などの計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB SQL を主体にして営業日ベースの窓を扱う設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 再利用性とテスト性
  - OpenAI 呼び出し部を内部関数として分離し、テスト時に差し替え可能（unittest.mock.patch を想定）。
  - API キー注入（api_key 引数）や環境変数参照の設計によりテスト容易性を確保。
  - DuckDB に対して BEGIN / DELETE / INSERT / COMMIT の冪等書き込みパターンを採用。

Security / Safety / Reliability
- ルックアヘッドバイアス防止のため内部で現在日時を直接参照しない設計を徹底（target_date を引数として扱う）。
- OpenAI/外部 API 呼び出しはリトライ戦略とフォールバック値（0.0 やスキップ）を採用して処理の耐障害性を向上。
- .env パーサにおけるエスケープとコメント処理により機密トークンの誤読み込み防止を試みる。
- DuckDB executemany の互換性（空リストバインドの回避）を考慮した実装。

Known issues / Limitations
- 一部コードは外部モジュール（jquants_client, quality 等）への呼び出しを前提としており、これらは本リポジトリに含まれていません。実行にはそれらの実装/モックが必要です。
- data/__init__.py が空のままで、公開 API の整理は今後の作業対象です。
- pipeline モジュール末尾の _get_max_date の実装が途中と思われる断片が存在します（実行時に該当部分の補完が必要）。
- 実行環境では OpenAI SDK のバージョン差異（status_code の有無等）に配慮した実装を行っていますが、将来の SDK 変更により追加対応が必要になる可能性があります。

Developer notes（設計方針の要約）
- DuckDB を分析 DB として使用（SQL + Python のハイブリッド実装）。
- 外部ネットワーク呼び出しは失敗を許容してフォールバックする（フェイルセーフ設計）。
- 日付の扱いはすべて naive な date / datetime で統一し timezone 汚染を避ける。
- DB 書き込みは冪等性を重視し、部分失敗時に既存データを不必要に消さない方針。

Acknowledgements
- 本リリースは初期実装のため、機能追加・リファクタ・テスト追加を今後継続して実施します。バグ報告や改善提案は歓迎します。