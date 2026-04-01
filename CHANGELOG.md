# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース履歴
- [Unreleased]
- [0.1.0] - 2026-04-01

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージメタ情報として `__version__ = "0.1.0"` を設定。
  - パッケージの公開 API に data, strategy, execution, monitoring を含めるエクスポート設定を追加。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - .env パーサーは `export KEY=...`、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮。
    - OS 側の環境変数をプロテクトするための上書き制御（`.env` は既存変数を上書きしない、`.env.local` は上書き可）を実装。
  - 必須変数チェック用のヘルパー `_require` と `Settings` クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境フラグ等）。
  - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値チェック）を実装。
  - パス系の設定値は `pathlib.Path` で返す（`expanduser` を適用）。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp モジュールを追加（score_news）。
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチでセンチメントスコアを取得。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算するユーティリティを実装（UTC naive datetime で返却）。
    - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE）、1銘柄当たり最大記事数・最大文字数でトリムする保護機構。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ）を実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、コード検証、数値性、クリップ）を実施。失敗時は個別チャンクをスキップし全体の処理継続を保証。
    - DuckDB への書き込みは部分的冪等性を考慮（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所を置き換え可能に設計（内部 _call_openai_api を参照）。
  - regime_detector モジュールを追加（score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200 比率算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）と、raw_news からマクロキーワード抽出処理を実装。
    - OpenAI 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - リトライ・バックオフ戦略を実装してサービスの揮発的エラーに耐性を持たせている。

- データ（DataPlatform）モジュール (kabusys.data)
  - calendar_management を追加（JPX カレンダー管理）。
    - market_calendar テーブルの利用を前提とした営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録がない場合は曜日ベース（土日非営業）でのフォールバックを行う。DB の値を優先。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等的に保存。バックフィル（直近数日再取得）・健全性チェックを実装。
  - ETL / pipeline
    - ETLResult データクラスを追加（ETL 実行結果の集約: 取得数・保存数・品質問題・エラーまとめ）。
    - pipeline モジュールの型（ETLResult）の再エクスポートを提供。
    - ETL の設計方針として差分取得・バックフィル・品質チェックの集約（致命的エラーでも全件チェック継続）などを明文化。

- 研究（Research）モジュール (kabusys.research)
  - factor_research を追加
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL によって計算する関数群（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の扱い（条件を満たさないと None を返す）を定義。
  - feature_exploration を追加
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
    - スピアマンの順位相関（ランク → Pearson）による IC 算出を実装。

- 共通実装
  - DuckDB を主要なローカル分析 DB として利用する設計で各モジュールが DuckDB 接続を受け取るインターフェースを採用。
  - ログ出力（info/warning/debug）を各モジュールに実装して運用監視を支援。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 未実装 / 制限事項（このリリースで明示）
- バリューファクターの一部（PBR、配当利回り）は現バージョンでは未実装（calc_value の docstring に明記）。
- ETL pipeline の一部低レベルユーティリティ（pipeline モジュールの末尾等）で未完のコード断片がある可能性あり（リポジトリ全体の継続的整備が必要）。
- OpenAI API 利用は外部依存（API キー必須）。API 呼び出しのコストや率制限に注意。
- news_nlp / regime_detector は LLM の応答品質に依存するため、運用時には監視とヒューマンレビューが推奨される。

### セキュリティ (Security)
- 初期リリースのため該当なし。ただし、環境変数に API キー等の機密情報を想定しているため、運用時は .env や実行環境のアクセス制御に注意。

---

その他: 各モジュールの設計方針として「ルックアヘッドバイアスの排除」「DB 書き込みの冪等性」「API 障害に対するフェイルセーフ」「テスト容易性（API 呼び出し箇所の差し替え可能性）」が明文化されています。運用・拡張時はこれらの前提を尊重して変更を行ってください。