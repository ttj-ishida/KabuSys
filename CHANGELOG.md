KEEP A CHANGELOG準拠の CHANGELOG.md（日本語）
※コードベースから機能・設計方針を推測して記載しています。

Unreleased
---------
- なし（現時点でリリース済みの初期バージョンのみ）

0.1.0 - 初期リリース
-------------------
Added
- パッケージ基盤
  - kabusys パッケージの初期公開。サブパッケージとして data, research, ai, などをエクスポート。
  - package version を src/kabusys/__init__.py にて "__version__ = '0.1.0'" として管理。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定値をプロパティ経由で取得。必須値未設定時は明示的なエラーを投げる。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。
  - デフォルトの DB パス（DuckDB, SQLite）や Kabu API base URL のデフォルト値を設定。

- ニュースNLP & 市場レジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチサイズ・記事件数・文字数制限（過大トークン対策）を導入し、最大20銘柄/チャンクなどで処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対して指数バックオフでリトライ。
    - レスポンスを厳密にバリデートして ai_scores テーブルへ冪等的に書き込む（DELETE→INSERT）。部分失敗時に既存データを保護する実装。
    - ルックアヘッドバイアス対策として datetime.today() を参照せず、target_date ベースでウィンドウを計算。
    - API キーは引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ日次で冪等書き込み。
    - マクロニュースはキーワードリストでフィルタ（複数日本語・英語キーワード）。
    - OpenAI 呼び出しは専用関数で実施し、API失敗時は macro_sentiment=0.0 として処理を継続（フェイルセーフ）。
    - LLM 呼び出しのリトライ/バックオフや JSON パース例外の取り扱いを実装。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を参照した営業日判定とユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のときは曜日ベースのフォールバック（週末を休場扱い）。
    - DB 登録値優先で未登録日は一貫した曜日フォールバックを適用。
    - calendar_update_job により J-Quants からの差分取得と冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集計: 取得数・保存数・品質問題・エラーメッセージ等）。
    - 差分更新・バックフィル・品質チェック（quality モジュール連携）を行う ETL 用の基盤を実装（詳細は pipeline モジュール）。
  - jquants_client との連携を想定した差分取得・保存フローに対応（fetch / save 呼び出しを利用）。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - Volatility/Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（欠損取り扱いあり）。
    - Value: latest 財務データ（raw_financials）と株価を組み合わせて PER, ROE を計算。
    - DuckDB 上の SQL とウィンドウ関数を活用した高効率な実装。
  - feature_exploration:
    - 将来リターン計算（複数ホライズン）、Spearman（ランク）ベースの IC 計算、ランク関数（同順位は平均ランク）、
      ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等への依存を避け、標準ライブラリのみで実装。
  - 研究用ユーティリティ（zscore_normalize 等）は data.stats から提供される想定。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キー等の機密情報は Settings 経由で必須チェックを行い、.env ファイルの自動ロードは明示的に無効化可能。

設計・実装上の主な注意点（ドキュメント的なポイント）
- ルックアヘッドバイアス防止: date/today の直接参照を避け、すべて target_date を明示的に受け取る設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は極力処理を停止せずフォールバック（例: macro_sentiment=0.0、スキップ）して全体の安定性を優先。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT など）で実装。
- リトライ/バックオフ: レート制限や一時的なネットワーク障害に対して指数バックオフを実装。
- DuckDB 互換性: executemany 呼び出しの空リスト制約等、DuckDB の挙動に配慮した実装。

今後の TODO（推測）
- ai モジュールのユニットテスト（OpenAI 呼び出しのモック化）強化。
- jquants_client の具体的実装と ETL pipeline の統合テスト。
- モニタリング・通知（Slack 連携等）の実装（Settings に Slack 設定あり、連携実装は別途の可能性あり）。

参考
- 主要モジュール:
  - kabusys.config: 環境変数管理・.env パーサ
  - kabusys.ai.news_nlp / regime_detector: ニュース解析・レジーム判定（OpenAI 使用）
  - kabusys.data.calendar_management / pipeline: カレンダー管理・ETL 基盤
  - kabusys.research.*: ファクター計算・特徴量解析ユーティリティ

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴・コミットログが存在する場合はそれらを基に更新してください。）