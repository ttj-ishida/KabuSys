# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

なお、本リリースノートはソースコードの実装およびドキュメンテーション文字列（docstring）から推測した機能・設計意図を要約したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

- 今後のリリース候補としてのメモのみ。現状の初期リリースは 0.1.0。

---

## [0.1.0] - 2026-03-31

Added
- パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を定義。
  - パッケージ公開対象モジュール: data, strategy, execution, monitoring（__all__ に登録）。
- 環境設定管理モジュールを追加（kabusys.config）。
  - .env/.env.local からの自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - OS 環境変数を保護する protected 機構、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止をサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）などの設定をプロパティ経由で取得。
  - 環境変数未設定時の明確なエラーメッセージ（_require）や値検証（env, log_level）のバリデーションを実装。
- AI 関連モジュールを追加（kabusys.ai パッケージ）。
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）。
    - raw_news / news_symbols を集約し銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON モードでスコアリング。
    - バッチ処理（最大20銘柄/チャンク）、トリム（記事数上限・文字数上限）、再試行（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト構造、コード・スコア検証）、スコアを ±1.0 にクリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）を採用し、部分失敗時に既存スコアを保護する実装。
    - テスト向けに内部の OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
  - 市場レジーム判定（kabusys.ai.regime_detector）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で market_regime に書き込み。
    - LLM 呼び出しは JSON 出力想定、再試行戦略を実装。API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - DuckDB クエリでルックアヘッドバイアスを避ける（target_date 未満のみ参照）など、ML に配慮した設計方針を採用。
- リサーチ用ユーティリティを追加（kabusys.research）。
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等のファクター計算を提供。
    - DuckDB を用いた SQL 実装で、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズンに対応）、IC（スピアマンランク相関）calc_ic、rank、統計サマリー factor_summary を実装。
    - 外部ライブラリ非依存の純 Python 実装。
- データプラットフォーム関連を追加（kabusys.data）。
  - calendar_management:
    - market_calendar 管理、営業日判定（is_trading_day/is_sq_day）、前後営業日取得（next_trading_day/prev_trading_day）、期間内営業日列挙（get_trading_days）。
    - JPX カレンダーの夜間差分取得ジョブ calendar_update_job（J-Quants クライアント経由）を実装。バックフィル・健全性チェックあり。
  - ETL パイプライン（kabusys.data.pipeline / etl）。
    - ETLResult データクラスを定義（取得件数、保存件数、品質検査結果、エラーメッセージ等を保持）。
    - 差分取得・バックフィル方針・品質チェック設計を反映した処理骨子（jquants_client と quality モジュールを利用する想定）。
  - pipeline の公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。

Changed
- 設計全体: ルックアヘッドバイアス対策として各所で datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示的に受け取る API を優先）。
- DuckDB 書き込みは冪等性を重視（DELETE → INSERT／ON CONFLICT などを利用）し、部分失敗時の安全性を高める方針を明記。

Fixed
- .env パーサーの堅牢性向上（export プレフィックス対応、クォート中のエスケープ処理、インラインコメントの扱い、空行・コメント行の無視）。
- OpenAI レスポンスパース失敗や API エラー時に例外を投げずフォールバックするロジックを追加（サービスの可用性を優先）。

Security
- 環境変数の読み込みで OS 環境変数を保護する protected 機構を導入（.env による上書きを回避可能）。
- OpenAI API キーは明示的に引数で注入可能（テスト容易性）で、未設定時は ValueError を返して明示的に扱う。

Notes / Known limitations
- OpenAI クライアントは外部ライブラリ（openai）を利用しており、実行環境での API キーとネットワーク接続が必要。
- news_nlp と regime_detector はそれぞれ独立して OpenAI 呼び出しの private helper を持つ（モジュール結合を避ける設計）。テスト時は各モジュール内の _call_openai_api をパッチすることが意図されている。
- 一部の DuckDB バインド挙動（executemany に空リストを渡せない等）を考慮した実装が入っているため、DuckDB のバージョン互換性に依存する可能性あり。
- strategy / execution / monitoring モジュールは __all__ に含まれるが、この差分には具体的実装が含まれていないため、将来的な拡張部分として残る。

---

今後の予定（想定）
- strategy / execution / monitoring の具体実装追加（実際の売買ロジック、発注ラッパー、プロセス監視等）。
- テスト補強（ユニットテスト・統合テスト、OpenAI 呼び出しのモック/スタブ化）。
- ドキュメント整備（API リファレンス、運用手順、ETL/カレンダージョブの実運用ガイド）。

もし特定ファイルや変更点に関してより詳細なエントリ（例えば個別関数の変更履歴や設計判断の補足）を追加したい場合は、どの箇所に焦点を当てるか教えてください。