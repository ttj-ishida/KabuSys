# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお、本 CHANGELOG はリポジトリ内のコードおよび各モジュールの docstring から推定して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。本リリースは日本株向けのデータ基盤・リサーチ・AI 支援・環境設定ユーティリティ群を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ（version 0.1.0）
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD 非依存）
  - .env のパース機能を充実
    - export 構文対応、クォート文字内のバックスラッシュエスケープ処理、コメント処理（インラインコメントの取り扱い）
  - Settings クラスを提供（settings インスタンス）
    - 必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値やバリデーション（KABUSYS_ENV, LOG_LEVEL）
    - DuckDB/SQLite のデフォルトパス設定

- AI モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出
    - バッチ処理（最大 20 銘柄/リクエスト）とトークン肥大対策（記事数・文字数トリム）
    - JSON Mode を期待しつつ前後ノイズ混入時の復元ロジック
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ）
    - レスポンス検証（results リストの存在・型・既知コードフィルタ・数値性）
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）保存
    - テストしやすさのため OpenAI 呼び出し部分は内部関数をパッチ可能（unittest.mock.patch 用意）
  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - LLM 呼び出しは独立実装でモジュール結合を避ける
    - API キー検査、マクロニュース抽出、MA200 比率計算、スコア合成、market_regime テーブルへの冪等書き込みを実装
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ
    - リトライ（429/接続/TIMEOUT/5xx）と JSON パースの堅牢化

- データ基盤（kabusys.data）
  - calendar_management（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装
    - market_calendar を参照した営業日判定ユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - バックフィル、lookahead、健全性チェックなどの運用配慮を実装
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）
    - 差分更新・バックフィル・品質チェック設計に基づく ETL の補助ロジック実装
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装
    - ETL の結果を辞書化する to_dict（品質問題は簡易タプルで出力）
    - J-Quants クライアント（jquants_client）との連携を想定した設計（差分取得・保存は jquants_client に委譲）
  - その他
    - DuckDB 関連の注意点を考慮（executemany に空リストを与えない等）

- リサーチ（kabusys.research）
  - factor_research（モジュール）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離の計算（calc_momentum）
    - ボラティリティ / 流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比（calc_volatility）
    - バリュー: PER、ROE（raw_financials から最新値を取得して calc_value）
    - DuckDB を用いた SQL ベースの計算実装（外部 API にはアクセスせず）
    - 結果は (date, code) をキーとする dict のリストで返却
  - feature_exploration（モジュール）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力バリデーション）
    - IC（Spearman rank / calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数から取得する設計
- .env 自動ロードはプロジェクトルートに依存し、明示的フラグで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

注意事項・運用メモ（コードからの想定）
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を要求します。未設定時は ValueError を送出します。
- LLM 呼び出しは外部 API の失敗に対してフェイルセーフ（スコア 0.0 / スキップ）を採用しており、致命的エラーにならない設計です。
- DuckDB に依存する処理はテーブル存在チェックや executemany の空リスト回避等の実運用での注意をコード内に反映しています。
- calendar_update_job 等は外部 API（jquants_client）の実装依存です。ETL の差分取得・保存は jquants_client を経由する想定です。
- テスト容易性のため、OpenAI 呼び出し内部関数（_kabusys.ai.*._call_openai_api）を patch してモック化できるように設計されています。

（以上）