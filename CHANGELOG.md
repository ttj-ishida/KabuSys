CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
慣例に従いセクションは Unreleased → リリース順に並びます。

Unreleased
----------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-04
-------------------

初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しています。主な追加点は以下のとおりです。

Added
- パッケージ基盤
  - パッケージのバージョンを設定: __version__ = "0.1.0"
  - パッケージの公開 API を定義: __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
    - export KEY=val 形式やシングル/ダブルクォート・エスケープ、コメント処理に対応したパーサ実装
    - ファイル読み込み失敗時に警告を出力
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能
    - J-Quants / kabu ステーション / LINE API / DB パス / 監視設定 / システム設定等のプロパティを実装
    - 必須項目未設定時は ValueError を送出する _require() を提供
    - KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装
    - デフォルトの DB パス（DuckDB/SQLite）と PID/KILL フラグの既定値を設定

- データモジュール (kabusys.data)
  - ETL パイプライン結果型の公開インターフェース (ETLResult)
    - ETL 実行結果を格納する dataclass を実装（品質問題・エラーの集約、辞書化サポート）
  - pipeline モジュール（ETL の基盤ロジック）
    - 差分更新・バックフィル・品質チェックを想定した設計とユーティリティを実装
    - DuckDB と結合して動作する想定
  - calendar_management モジュール（マーケットカレンダー管理）
    - JPX カレンダーの管理・夜間更新ジョブ (calendar_update_job)
    - 営業日判定・前後営業日取得・期間内営業日列挙・SQ 判定などのユーティリティを実装
    - market_calendar が未取得の場合は曜日（平日）ベースでフォールバックする設計
    - DB 登録値優先、未登録日を曜日フォールバックで補完する一貫した挙動
    - 最大探索日数やバックフィル、健全性チェック等の安全機構を搭載
  - jquants_client / quality 等のクライアントモジュールを参照する設計（実際の API 呼び出しは jquants_client に委譲）

- 研究（Research）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装
    - DuckDB 上の prices_daily / raw_financials を前提に SQL と Python を組み合わせて高速に計算
    - データ不足時の None 扱いやログ出力など堅牢性を考慮
    - 結果は (date, code) を含む dict のリストで返却
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、入力検証あり
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装、最小レコード数チェックあり
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めによる ties 対策あり
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、記事数/文字数のトリム、レスポンス検証、スコアクリッピング（±1.0）を実装
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理、致命的ではないエラーはスキップして継続するフェイルセーフ設計
    - テスト容易性のため _call_openai_api をモックで差し替え可能
    - タイムウィンドウ計算（JST ベース → UTC naive datetime）を calc_news_window で提供（ルックアヘッド防止方針を遵守）
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
    - prices_daily から MA200 乖離を計算、raw_news からマクロキーワードで記事抽出、OpenAI で macro_sentiment を評価
    - レジームスコア合成、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API リトライ、JSON パース失敗時のフォールバック（macro_sentiment = 0.0）、テスト用差し替えポイントあり
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / Important
- API キー要件
  - OpenAI を利用する機能（score_news / score_regime）は OPENAI_API_KEY を要求します（関数引数で注入可能）。未設定時は ValueError を送出します。
  - J-Quants や kabu ステーション等の実働連携にはそれぞれの環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が必要です（Settings のプロパティ参照）。
- データベース
  - デフォルトで DuckDB を利用する想定。デフォルトパスは data/kabusys.duckdb、監視用 SQLite は data/monitoring.db。
- 設計方針の強調
  - ルックアヘッドバイアス防止（内部での現在時刻参照回避）
  - DB への冪等書き込み（部分失敗時も既存データを保護）
  - OpenAI 呼び出しに対する堅牢なリトライ / フォールバック設計
  - DuckDB 0.10 系等への互換性考慮（executemany の空リスト回避など）
- テスト支援
  - AI モジュールの内部 API 呼び出しポイント（_kabusys.ai.*._call_openai_api）を unittest.mock で差し替え可能
  - 環境自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）によりテスト環境での副作用を抑制可能

今後の予定（草案）
- strategy / execution / monitoring モジュールの追加実装（現状はパッケージ API に名前が含まれる）
- より詳細な品質チェックルールとモニタリング・アラートの実装
- ドキュメント強化（使用例・運用手順・API クライアント実装例）

―――

参照: この CHANGELOG はソースコード（src/kabusys 以下）の実装と docstring / コメントから推測してまとめています。必要であれば、各モジュールの詳細な使用例やリリースノートの追記を作成します。