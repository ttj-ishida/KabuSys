CHANGELOG
=========

すべての重要な変更は Keep a Changelog 規約に従って記載しています。  
初回リリースに相当する内容を、コードベースから推測してまとめています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- 基本パッケージ初期リリースを追加
  - パッケージ名: kabusys
  - パッケージバージョン: 0.1.0

- 環境設定管理機能を追加（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出は __file__ を基点に `.git` または `pyproject.toml` を探索するため、CWD に依存しない。
  - .env パーサーは以下をサポート:
    - コメント行、`export KEY=val` 形式
    - シングル/ダブルクォートとバックスラッシュエスケープの処理
    - クォートなしでのインラインコメント処理（直前がスペース/タブの場合）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 既存 OS 環境変数を保護するための上書き制御（override/protected）を実装。
  - Settings クラスを提供し、J-Quants トークン、kabuAPI パスワード、LINE トークン、DB パス、監視閾値、環境名・ログレベル等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。

- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントをスコアリングし ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）と記事集約ロジックを提供。
    - バッチ送信（最大 20 銘柄）・1銘柄あたりの最大記事数・最大文字数トリム等のトークン肥大化対策を導入。
    - JSON Mode を利用したモデル呼び出し、429・ネットワーク断・タイムアウト・5xx への指数バックオフによるリトライを実装。
    - レスポンス検証（JSON の抽出/検証、未知コード無視、スコア範囲クリップ）を実装。
    - DuckDB の executemany の制約（空リスト不可）を考慮した安全な DB 更新ロジック（DELETE → INSERT、部分失敗時は既存データ保護）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - regime_detector: ETF（1321）200日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - ma200 乖離計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）とマクロニュース抽出。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しないことでモジュール結合を低減）。
    - API エラーやパース失敗時はフェイルセーフにより macro_sentiment=0.0 を採用。
    - リトライ/バックオフ、5xx の扱い、ロギングを丁寧に実装。

- データ層（kabusys.data）を追加
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベース（土日）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックという一貫した挙動。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得→保存するロジックを提供。バックフィル・健全性チェックを含む。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行の集計情報・品質問題・エラーを保持）。
    - ETL パイプラインの設計方針（差分更新、バックフィル、品質チェックの扱い）を実装方針として定義。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - etl を外部公開するための簡易再エクスポート（kabusys.data.etl -> ETLResult）。

- 研究用モジュールを追加（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離を計算（DuckDB SQL を活用）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務データの取得ロジック含む）。
    - DuckDB ベースの実装で、外部 API には依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括クエリで計算。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（None/不正値/サンプル数チェックあり）。
    - rank: 同順位は平均ランクで扱うランク付け実装（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median の基本統計を計算（None 値除外、標準ライブラリのみ）。

- パッケージ公開インターフェース
  - __all__ に主要なサブパッケージ（data, strategy, execution, monitoring）を設定（パッケージ構成を明示）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI API キー未設定時は明確な ValueError を発生させることで誤った呼び出しを防止（news_nlp.score_news / regime_detector.score_regime）。
- .env 自動ロードはテスト用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / 実装上の重要な設計判断（ドキュメント的記載）
- いずれの AI 処理（news_nlp / regime_detector）も datetime.today() や date.today() を直接参照しない実装を採用し、ルックアヘッドバイアスを防止。
- DuckDB の挙動（executemany に空リストを渡せない等）に合わせた DB 更新の防護策を実装。
- API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行し、最終的に安全なデフォルト（スコア 0.0、またはそのチャンクのスキップ）で継続するフェイルセーフ設計。
- 各所で BEGIN / DELETE / INSERT / COMMIT の冪等書き込みパターンを採用し、例外時は ROLLBACK を試みてログ出力する。

Acknowledgements / 既知の制約
- OpenAI 呼び出し部分は OpenAI Python SDK に依存するため、実行環境における SDK バージョン差分や API レスポンス形式の変化に注意が必要。
- 一部関数は DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とするため、初期セットアップでテーブル定義が必要。

今後提案（例）
- strategy / execution / monitoring の具体実装を追加して、自動売買フローを統合する（現時点はモジュールエントリのみ）。
- テストカバレッジの強化（特に OpenAI 呼び出し・DB トランザクション周りの単体テスト）。
- エラー/メトリクスの可観測化（Prometheus / Sentry 等）を追加。