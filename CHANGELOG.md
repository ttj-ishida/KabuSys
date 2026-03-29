# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは Keep a Changelog の慣例に従っています。  

- リリース日はコミット時点（この CHANGELOG 作成日）を基準にしています。  

## [Unreleased]

- （未リリースの変更はここに記載）

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ基本構成
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。パッケージバージョンは 0.1.0 に設定。

- 環境設定・自動 .env ロード（kabusys.config）
  - .env / .env.local の自動読み込み機能を提供（プロジェクトルートを .git または pyproject.toml で探索）。
  - export KEY=val 形式やクォート・エスケープ、行内コメントの扱いを考慮したパーサ実装。
  - OS 環境変数の保護（読み込み時に既存環境変数を上書きしない、.env.local は上書き可能）と自動読込無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスによる型付きプロパティ（J-Quants トークン、kabu API、Slack トークン・チャネル、DB パス、環境・ログレベル判定等）を提供。
  - 環境変数検証（必須キー未設定時の ValueError、KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- データプラットフォーム関連（kabusys.data）
  - DuckDB を前提とした ETL・パイプライン用ユーティリティ（pipeline.ETLResult の公開再エクスポート）。
  - 市場カレンダー管理（calendar_management）:
    - market_calendar テーブルの状態に基づく営業日判定・前後営業日取得・期間内営業日の列挙。
    - DB 未取得時は曜日ベースでフォールバックする堅牢なロジック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）。
    - is_sq_day 判定など取引カレンダーに関するユーティリティ。
  - ETL パイプライン（data.pipeline）:
    - 差分フェッチ、保存（Idempotent な save_* 呼び出し）、品質チェック統合を想定した ETLResult 型を実装。
    - 最終取得日の判定、バックフィル期間、品質チェック結果収集をサポート。

- ニュース NLP / AI 機能（kabusys.ai）
  - news_nlp モジュール:
    - raw_news / news_symbols を集約し、銘柄ごとのニューステキストを生成。
    - OpenAI（gpt-4o-mini）に対するバッチ送信によるセンチメントスコア算出と ai_scores テーブルへの書き込み処理（チャンク処理、最大銘柄数・トリム長の制限）。
    - JSON Mode に対するレスポンスの堅牢なバリデーション（余計な前後テキストの復元、results フィールドチェック、コードの正規化、スコアの数値検証、±1.0 クリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。API 例外時は個別チャンクをスキップして全体処理を継続（フェイルセーフ）。
    - calc_news_window による JST ベースのニュース集計ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 時刻範囲）。
  - regime_detector モジュール:
    - ETF（コード 1321）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロニュースの抽出、OpenAI 呼び出しによるセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時には macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - OpenAI クライアント呼び出しはモジュール単位で独立実装（テスト時に差し替え可能）。

- 研究用ファクター・特徴量探索（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、
      流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB SQL により計算。
    - データ不足時の None 処理、営業日ベースのホライズンスキャン設計。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、
      値をランクに変換するユーティリティ、ファクター列の統計サマリーを純粋 Python 実装（外部依存なし）。
  - research パッケージは主要関数を再エクスポートして研究用途の API を提供。

### Design / Reliability Notes（設計上の留意点）
- ルックアヘッドバイアス防止
  - AI モジュール・ファクター計算等は内部で datetime.today() / date.today() を参照せず、明示的な target_date を受け取る方針。
  - DB クエリは target_date 未満や窓範囲制約を利用して未来データの参照を避ける。

- 可観測性とログ
  - 各モジュールで詳細な info/debug/warning ログを出力するよう実装。

- DB 書き込みの冪等性
  - market_regime / ai_scores / market_calendar 等への書き込みは削除→挿入や ON CONFLICT 相当の扱いで冪等性を確保。

- フェイルセーフ設計
  - OpenAI API エラーやデータ不足時に例外で全体を停止させず、既存スコアやデータを保護しつつ処理を継続するコードパスを用意。

### Security
- 環境変数の取り扱い
  - 必須の機密情報（OpenAI API キー、J-Quants / Slack / kabu API パスワード等）は Settings の必須プロパティでチェックし、未設定時に明示的エラーを出す。
  - OS 環境変数を .env による上書きから保護する仕組みを実装。

### Compatibility / Dependencies
- DuckDB をデータストアとして利用する実装。
- OpenAI SDK を利用（gpt-4o-mini モデルを前提）。API レスポンス形式は JSON Mode（response_format={"type":"json_object"}）を想定。
- 外部依存（pandas 等）を避け、標準ライブラリ + DuckDB + OpenAI SDK で動作するよう設計。

---

注: この CHANGELOG は、提示されたコードベースから推測できる機能・設計方針を基に作成しています。実際のリリースノートとして利用する場合は、テスト結果・マイナーバグ修正・既知の制約などを追加してください。