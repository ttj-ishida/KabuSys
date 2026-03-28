CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。  
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

Added
- 初回リリース。基本的な日本株リサーチ / データ / AI 支援モジュール群を追加。
  - パッケージのエントリポイントを定義
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - 公開モジュール: data, strategy, execution, monitoring（__all__ 経由）

- 環境設定 / .env ローダー（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装（.env, .env.local の順、OS 環境変数は保護）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env のパースは次の仕様に対応：
    - 空行・コメント行（#）をスキップ
    - export KEY=val 形式を許容
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理
    - クォートなしの行で # の直前が空白/タブの場合はインラインコメントとして扱う
  - Settings クラスを提供し、必要な環境変数の取得とバリデーションを行う（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - システム設定の検証: KABUSYS_ENV は development / paper_trading / live のみ許可。LOG_LEVEL は標準的なログレベルのみ許可。
  - データベースのパス設定（DUCKDB_PATH, SQLITE_PATH）を Path として提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB クエリ）。
    - 1銘柄あたり最大記事数・文字数でトリム（過度なプロンプト肥大を防止）。
    - バッチ処理（デフォルト20銘柄/コール）とエクスポネンシャルバックオフを実装（429, ネットワーク断, タイムアウト, 5xx をリトライ対象）。
    - レスポンスの厳密なバリデーションを行い、ai_scores テーブルへ冪等的（DELETE→INSERT）に書き込み。
    - フェイルセーフ: API 呼び出しやパース失敗は例外を投げず該当チャンクをスキップ（全体処理継続）。
    - テストしやすさのため OpenAI 呼出しを _call_openai_api 関数で切り出し、unittest.mock.patch による差し替えを想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - 日次で市場レジーム（bull / neutral / bear）を判定。
    - 指標: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、LLM（gpt-4o-mini）により JSON で macro_sentiment を取得。
    - API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコアのクリップと閾値に基づくラベリングを行い、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時は ROLLBACK を試みて例外を再送出。
    - OpenAI 呼出しは独立実装で、news_nlp とはプライベート関数を共有しない設計。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータが存在しない場合は曜日ベース（土日除外）でフォールバックする一貫したロジックを採用。
    - next/prev_trading_day 等は探索上限（デフォルト 60 日）を設け、無限ループを防止。
    - calendar_update_job を実装し、J-Quants からの差分取得と冪等保存（ON CONFLICT 相当）を行う。バックフィルと健全性チェックを実施。
    - jquants_client との連携を想定（fetch/save 関数経由）。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - 差分取得、保存、品質チェックを行う設計方針を文書化（backfill, 品質チェックは重大度情報を返す等）。
    - DuckDB を前提とした最大日付取得やテーブル存在チェック等のユーティリティを実装。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）
    - ボラティリティ/流動性（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - バリュー（PER、ROE を raw_financials から取得）
    - DuckDB の SQL を用いた計算実装。結果は date, code を含む dict リストで返す。
    - データ不足時は None を返す設計（安全性確保）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、horizons のバリデーション有り）
    - IC（Information Coefficient）計算（Spearman 相当のランク相関）
    - ランク付けユーティリティ（同順位は平均ランク）
    - ファクター統計サマリー（count/mean/std/min/max/median）を実装
    - pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで動作する方針。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーは引数で注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照する。キーが未設定の場合は ValueError を送出。
- .env 自動ロード時に OS 環境変数は保護される（.env が既存の OS 環境変数を上書きしない）。

Notes / 既知の設計上の注意点
- ルックアヘッドバイアス回避
  - AI モジュールや研究モジュールは datetime.today() / date.today() を内部参照せず、必ず target_date を引数で受け取る設計になっている。バックテスト / 再現性の観点で安全。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）への依存箇所は失敗時に処理を継続するか安全なデフォルト（例: macro_sentiment=0.0）にフォールバックするよう設計されている。
- テスト可能性
  - OpenAI 呼び出しは内部で _call_openai_api を切り出しており、ユニットテストで差し替え可能。
- 依存
  - DuckDB および openai SDK（OpenAI クライアント）の利用を想定。環境変数や API クライアントのセットアップが必要。

今後の改善案（想定）
- ニュース本文の言語検出や記事の重複除外ロジック強化
- ai_scores / market_regime のスキーマバージョン管理・マイグレーションツール
- OpenAI の別モデル対応やコスト最適化用のバッチ戦略の追加
- エンドツーエンドの統合テスト用のテストフィクスチャ提供

----