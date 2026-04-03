KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
重大な変更は Breaking Changes セクションで明記します。

Unreleased
----------

（現在の配布はありません）

0.1.0 - 2026-04-03
-----------------

初回リリース。以下の機能群と主要設計判断を実装しています。

Added
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に基づく想定）。

- 環境設定管理（kabusys.config）
  - .env ファイル自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境 > .env.local > .env。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - .env パーサ実装: export 文対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無で異なるルール）。
  - 保護キーを使った上書き制御（既存 OS 環境変数を保護）。
  - Settings クラスでアプリ設定をプロパティ経由で取得（J-Quants / kabu / LINE / DB パス / 監視設定 / システム設定 等）。
  - バリデーション: KABUSYS_ENV や LOG_LEVEL の許容値チェック。必須 env の未設定時は ValueError を送出する _require。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、ターゲットウィンドウ（前日15:00 JST〜当日08:30 JST）で記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのスコアを ai_scores に書き込みる。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode のレスポンスを検証・復元（前後余計なテキストが混ざるケースに対応）。
    - リトライ戦略: 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB の executemany の仕様差異を考慮（空リストの扱い回避）。
    - テスト容易性: API 呼び出し関数をモジュール内部で定義しており unittest.mock.patch で差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で regime_score/regime_label を market_regime テーブルへ冪等書き込み。
    - マクロニュースは事前定義のマクロキーワードでフィルタし、最大 20 件を LLM に渡す。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックして継続（例外を上げない）。
    - OpenAI 呼び出しは retries と exponential backoff を備え、5xx とその他エラーを分けてハンドリングする。
    - レスポンスは厳密 JSON（{"macro_sentiment": float}）を期待し、クリップ処理を行う。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等実装。失敗時は ROLLBACK を試みて例外を上位へ伝播。

- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得または該当日が未登録の場合、曜日ベースのフォールバック（週末を非営業日）で一貫した判定を行う。
    - 最大探索日数や lookahead/backfill の定数を導入し、無限ループ防止と API の訂正取り込みに対応。
    - calendar_update_job を実装し、J-Quants API から差分取得 → jq.save_market_calendar で冪等保存。健全性チェック（過度に未来の日付が存在する場合はスキップ）。

  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得・保存件数、品質問題、エラー一覧などを集約）。
    - 差分更新、バックフィル、品質チェックの設計方針に基づく処理枠組みを実装（jquants_client 経由での取得、quality モジュールによる検査）。
    - DuckDB のテーブル存在確認や最大日付取得などの内部ユーティリティを提供。
  - etl の public re-export（kabusys.data.etl: ETLResult を再エクスポート）。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER・ROE）を DuckDB 上の SQL で計算する関数を提供。
    - データ不足時の扱い（必要行数未満は None を返す）や、返却形式（date, code をキーにした dict のリスト）を規定。
    - パフォーマンス考慮：スキャン範囲にバッファを設定し、カレンダー日による上限で無駄な参照を抑制。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度のクエリで取得。horizons のバリデーションあり（1..252）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装。有効レコードが 3 未満の場合は None。
    - ランキング（rank）: 同順位は平均ランクで処理（浮動小数誤差対策の丸めあり）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None 値除外）。
    - pandas 等の外部依存を持たず、標準ライブラリと DuckDB で完結する実装。

Changed
- 設計方針の明文化
  - 多くのモジュールで「datetime.today()/date.today() を参照しない」ことでルックアヘッドバイアスを防ぐ設計を採用。
  - API 呼び出し失敗時は基本的に処理を中断せずフォールバック（スコア 0.0 やチャンクスキップ）して継続するフェイルセーフ方針を採用。
  - DuckDB のバージョン依存に配慮した実装（executemany の空リスト回避、list 型バインドの安定性問題回避）。

Fixed
- N/A（初回リリースにつき個別のバグ修正履歴はなし）

Security
- 環境変数の保護機構（.env ロード時に既存 OS 環境変数を protected として扱う）を実装し、予期せぬ上書きを防止。

Notes / 実装上の注意点
- OpenAI API
  - 実装は OpenAI の chat.completions.create（JSON mode）を前提とする。API の将来の SDK 変更（例: 例外クラスや status_code の有無）に耐性を持たせるためのガードを実装。
  - テストでは内部の _call_openai_api をモック／パッチして API 呼び出しを制御可能。

- DuckDB
  - executemany に対する空リストの制約（DuckDB 0.10 系）を回避するチェックを多数箇所に導入。

- フォールバック挙動
  - データ不足や API エラーが発生した場合、基本的にロジックはスコアを中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）にフォールバックするか、該当チャンクのみスキップして他の処理を継続します。これにより ETL/解析ジョブの停止を抑制しますが、上位で異常判定を行うことを想定しています（ETLResult に errors/quality_issues を集約）。

今後の予定（短期）
- 発注/実行モジュール（execution）や戦略モジュール（strategy）の実装・公開（初期の骨格はパッケージ構成に含まれますが、本バージョンでは主に Data/Research/AI 周りが実装済み）。
- 追加の品質チェックルール、監視・アラート（monitoring）機能の強化。
- OpenAI 呼び出しの更なる汎用化（複数モデル対応やコスト制御の追加）。

Contributing
- バグ修正や機能追加の提案は Pull Request を通じて受け付けます。コードの一貫性（DuckDB 互換性、ルックアヘッドバイアスの回避、テスト容易性）を維持してください。

--- 

この CHANGELOG はソースコードのコメント・実装に基づいて生成しています。追加の変更がある場合は逐次更新してください。