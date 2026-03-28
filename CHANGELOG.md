CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

[Unreleased]
------------

（次バージョン用のプレースホルダ）

[0.1.0] - 2026-03-28
--------------------

初回公開リリース。ライブラリ全体の骨格と主要機能を実装しました。主な追加点・設計方針は以下のとおりです。

Added
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パブリックモジュールのエクスポート定義を追加（data, strategy, execution, monitoring）。

- 環境設定 / ローダー（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
  - Settings クラスを提供し、主要な設定値（OPENAI / J-Quants / kabu/Slack / DB パス / 環境・ログレベル判定）をプロパティ経由で取得。KABUSYS_ENV と LOG_LEVEL の値検証、is_live / is_paper / is_dev の便利プロパティあり。

- AI（自然言語処理）機能（src/kabusys/ai/）
  - ニュースセンチメント（news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）の計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数制限、JSON mode を利用したレスポンス検証、429/ネットワーク/5xx に対する指数バックオフリトライ等の堅牢化。
    - レスポンス検証ルール（results 配列、code と score の検証、スコアのクリッピングなど）を実装。部分失敗時の DB 書き換え方針（影響を受けたコードのみ置換）により部分障害耐性を確保。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に（モジュール内の _call_openai_api をパッチ可能）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）とニュース LLM センチメント（30%）を合成し、日次で market_regime テーブルへ冪等的に書き込む処理を実装。
    - DuckDB クエリはルックアヘッドバイアスを防ぐため target_date 未満のデータのみ参照。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、API障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を行い、失敗時は ROLLBACK を試行。

- データ基盤（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）
    - market_calendar を使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動を実現。
    - カレンダーの夜間差分更新ジョブ calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック、save の呼び出し）を実装。
    - 検索上限（日数）やバックフィル日数などの安全策を導入。

  - ETL パイプライン（pipeline.py / etl.py）
    - 差分取得→保存→品質チェックという ETL の設計を実装。差分取得のデフォルト単位は営業日。
    - ETLResult データクラスを公開（etl.py で再エクスポート）し、取得数・保存数・品質問題・エラー情報・判定ヘルパーを提供。
    - J-Quants クライアント経由の idempotent な保存（ON CONFLICT DO UPDATE）を前提に実装。
    - DuckDB の executemany における互換性問題（空リスト不可）を考慮した実装を行い、部分書き換えで既存データ保護を実現。

- 研究用ユーティリティ（src/kabusys/research/）
  - Factor 計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装。prices_daily / raw_financials を参照。
    - データ不足時の None ハンドリングやスキャン範囲バッファを導入。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン calc_forward_returns（可変ホライズン、入力検証付き）。
    - ランク相関（Spearman に相当する IC）を計算する calc_ic、同順位の平均ランクを扱う rank、統計サマリー factor_summary を実装。
    - 外部依存を避け、標準ライブラリのみで完結する実装。

- ロギングと堅牢性
  - 各処理で詳細な logger メッセージを追加（INFO/DEBUG/WARNING/exception を適切に使用）。
  - API 呼び出し（OpenAI/J-Quants）に対するリトライ・フォールバック戦略を実装し、外部 API 依存時のフェイルセーフを提供。
  - すべての日付処理で timezone 混入を避け、date / naive datetime を明示的に扱う設計方針を採用（ルックアヘッドバイアス防止）。

Documentation / Examples
- モジュールの docstring に設計方針や処理フロー、入力条件・戻り値・副作用（DB 書き込み等）を明記。テストや運用での利用方法のヒントを含む。

Security
- 環境変数から API キーを取得する際の必須チェックを導入（未設定時は ValueError を送出）。（OpenAI: OPENAI_API_KEY, J-Quants: JQUANTS_REFRESH_TOKEN 等）
- .env ファイル読み込み時に OS 環境変数を保護する protected セットを導入（.env.local で上書き可能だが OS 側で設定されたキーは意図的に保護可能）。

Notes / Implementation details
- OpenAI とのやり取りは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）を利用する実装になっています。テストのために呼び出しを差し替え可能です。
- DuckDB を主要な一時 DB として想定。DuckDB バージョンや executemany の挙動差分に注意（コード内で説明あり）。
- いくつかの関数は「呼び出し側で API キーを渡す」ことで外部依存を注入可能（テスト容易化）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

既知の制限 / 今後の検討事項
- OpenAI API 呼び出しに関してはコスト・レイテンシの観点からさらに最適化（キャッシュ、より小さいモデル選択など）を検討する余地があります。
- news_nlp の出力スキーマ依存度が高いため、LLM の挙動変化に対する追加の堅牢化（スキーマ変換ルールや代替解析器）を検討中。
- ETL の並列化や大規模データ処理最適化は未実装（将来的に追加予定）。

---- 

注: この CHANGELOG はソースコード（src/ 以下）から実装内容・設計意図を推測して作成しています。実際のリリースノート作成時は追加の変更点や運用ドキュメントを反映してください。