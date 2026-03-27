CHANGELOG
=========
(このファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを使用します。)

Unreleased
----------
- なし（初回リリースは v0.1.0）

[0.1.0] - 2026-03-27
--------------------
Added
- 基本パッケージ情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - 公開 API に data, strategy, execution, monitoring を追加（__all__）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない。
  - 高度な .env パーサ実装（export 形式サポート、クォート内のエスケープ処理、インラインコメント処理）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected セットを用いた上書き制御（.env.local は上書きモード）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定をプロパティで取得可能に。
  - 設定値バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。必須環境変数未設定時は ValueError を投げる。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算ユーティリティを実装（calc_news_window）。
  - バッチ処理（1 API コールで最大 20 銘柄）・記事数・文字数のトリム制限を導入（トークン肥大化対策）。
  - レート制限 (429)、接続断、タイムアウト、5xx を対象とした指数バックオフのリトライ実装。
  - OpenAI の JSON Mode レスポンスのバリデーションと堅牢なパース（余計な前後テキストの復元含む）。
  - スコアは ±1.0 にクリップ、部分失敗時でも既存データを保護するために対象コードのみ DELETE→INSERT を行う冪等保存。
  - テスト容易性のため API 呼び出し部分を patch 可能に（_call_openai_api の差し替えを想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - MA 計算は target_date 未満のデータのみを使用することでルックアヘッドバイアスを排除。
  - マクロニュースの抽出（マクロキーワードによるフィルタ）と LLM 評価（gpt-4o-mini）を組み合わせ、API エラー時は安全に macro_sentiment=0.0 にフォールバック。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションロールバックの保護を実装。
  - API 呼び出しのリトライロジックと 5xx 判定の取り扱いを実装。テスト時に差し替え可能な内部呼び出し設計。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client の save_* による冪等保存）、品質チェック連携のための骨組みを実装。
    - ETLResult データクラスを公開（ETL 結果の構造化、品質問題の収集、エラー判定ユーティリティを含む）。
    - DuckDB を前提とした最大日付取得等のユーティリティを提供。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録あり → DB 優先、未登録日 → 曜日ベースのフォールバックという一貫したポリシーを採用。
    - 夜間バッチ更新ジョブ calendar_update_job を実装し J-Quants から差分取得・バックフィル・健全性チェックを行う。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) とバックフィル、先読み日数を設定して異常ケースを防止。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER、ROE）を DuckDB SQL ベースで実装。
    - データ不足時は None を返す安全設計、結果は (date, code) をキーとする辞書リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターンの計算（複数ホライズン、範囲チェック）。
    - IC（Spearman の ρ）計算、ランク変換ユーティリティ（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等に依存しない標準ライブラリ + DuckDB ベースの設計。

- その他
  - DuckDB を利用した SQL-heavy な実装で高速な集計・ウィンドウ関数利用を前提とした設計。
  - ロギングを各モジュールに導入し、警告/情報出力で異常時のフォールバック動作を可視化。

Security
- .env 読み込みでは OS 環境変数を protected として上書きを防止。
- 必須トークン（OpenAI / Slack / Kabu 等）が未設定の場合は明示的に例外を発生させて安全性を担保。

Known limitations / Notes
- OpenAI API（gpt-4o-mini）への依存があるため、利用には OPENAI_API_KEY の設定が必要。
- 一部外部クライアント（jquants_client）やテーブル定義はこの変更履歴の範囲外。実行には適切な DB スキーマと API クライアントの実装が必要。
- strategy / execution / monitoring の具体実装は公開 API に含まれるが（__all__）、今回のコードベースには詳細実装が含まれていないため別途実装が必要。

Acknowledgements
- 本リリースは DuckDB をデータ層の中核とし、OpenAI の JSON Mode を用いた LLM ベースのスコアリングを統合する設計を採用しています。

(注) 上記はコードの実装内容から推測して作成した CHANGELOG です。機能の動作・外部 API 依存関係については実際の実行環境・追加モジュールにより差異が生じる可能性があります。