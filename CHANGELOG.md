CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
このファイルは、リリースノートの簡潔な要約です。  
（内容はリポジトリ内のソースコードから推測して作成しています）

フォーマット: https://keepachangelog.com/ja/1.0.0/
タグ付け: Semantic Versioning に準拠

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: KabuSys (日本株自動売買システム) を公開。
  - バージョン: 0.1.0
  - パッケージトップ: kabusys.__version__ = "0.1.0"

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を自動読み込みするユーティリティを追加。
  - プロジェクトルートの特定: .git または pyproject.toml を基準に探索し、CWD に依存しない実装。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース/タブ規則）等に対応する堅牢なパーサ実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数チェック用ヘルパー (_require) と Settings クラスを提供。
  - 主要設定プロパティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) でセンチメントを算出して ai_scores テーブルへ保存。
    - JST ベースのニュースウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム、JSON Mode での堅牢なバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API 失敗時はスキップして継続（フェイルセーフ）。
    - レスポンスパース失敗や未知コードの扱いに対する安全策（不正レスポンスは無視、部分書き込みで既存データ保護）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch 用の内部関数フックあり）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) と、ニュース由来のマクロセンチメント (重み 30%) を合成して日次の市場レジーム（bull / neutral / bear）を算出して market_regime テーブルへ冪等的に書き込み。
    - マクロセンチメントはマクロキーワードでフィルタしたタイトル群を OpenAI に投げて JSON レスポンスをパース。
    - ルックアヘッドバイアス防止：prices_daily クエリは target_date 未満のデータのみを使用。
    - API 呼び出しのリトライ、パース失敗時は macro_sentiment=0.0 にフォールバック（例外を投げない）。
    - データベース操作はトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保、エラー時は ROLLBACK を行い上位へ伝播。

- データ管理 (kabusys.data)
  - 市場カレンダー管理 (calendar_management)
    - market_calendar を基に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day などのユーティリティを実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
    - 最大探索日数制限で無限ループを防止。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新、バックフィル、品質チェックの設計方針を実装するためのユーティリティ群（jquants_client, quality と連携する前提）。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - バリュー: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials から最新値を参照）
    - SQL → DuckDB を利用した計算。データ不足時の None 返却やログ出力を実装。

  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズンの将来終値を LEAD で取得しリターン計算（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 (calc_ic): スピアマンの順位相関を実装（同順位は平均ランクで処理）。
    - 基本統計サマリー (factor_summary) とランク付けユーティリティ (rank) を提供。
    - pandas 等の外部依存なしで標準ライブラリ + DuckDB で実装。

Changed
- 初回リリースのため該当なし（初期機能群の導入）。

Fixed
- 初回リリースのため該当なし。

Security
- AI 機能利用時は OpenAI API キーが必要。未設定時は ValueError を送出して明示的に失敗する設計（news_nlp.score_news, regime_detector.score_regime）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 環境変数はデフォルトで保護（.env が既存の OS 環境変数を上書きしない）。

Notes / Implementation details（実装上の重要ポイント）
- DuckDB を主要なローカル分析 DB として利用。SQL を多用して集計/ウィンドウ計算を行う設計。
- API 呼び出し周りは堅牢性重視（リトライ、バックオフ、フェイルセーフの既定動作）。
- JSON Mode を使った OpenAI 呼び出しを想定しつつ、実際に余計なテキストが混入するケースへの復元ロジックを実装。
- テスト容易性: OpenAI 呼び出し関数はモジュール内部で定義されており、テスト時に patch して差し替え可能。
- DB 書き込みは可能な限り部分置換（該当コードを限定して DELETE → INSERT）として、部分失敗が既存データを消さないよう配慮。

Known limitations / TODO（コードから推測される未着手事項）
- 一部ファクター（PBR・配当利回り）の未実装（calc_value の docstring に明記）。
- ai_score と sentiment_score は現フェーズで同値にして保存している点は将来的な仕様拡張余地あり。
- jquants_client / quality 等の外部モジュール実装に依存（コード内で import はされているが、実際の外部連携部分は別モジュール実装が必要）。
- DuckDB バインドの挙動差異（executemany と空リスト）の互換性対策を実装しているため、DuckDB バージョン差異に注意。

Authors
- コードベースから推測して作成（ソースコメント・設計注釈に基づくまとめ）。

ライセンス
- ソースコード側に明記がないためここでは省略。実際リポジトリの LICENSE を参照してください。