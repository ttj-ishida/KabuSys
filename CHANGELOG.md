Keep a Changelog 準拠の CHANGELOG.md（日本語）
=========================================

全体方針
--------
このプロジェクトはセマンティックバージョニングに従います。  
主な設計方針（コード中の注釈に基づく）:
- ルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照しない実装方針を採用しています（ターゲット日を明示的に渡す設計）。
- DuckDB をデータ保存・集計基盤として使用し、トランザクション（BEGIN / DELETE / INSERT / COMMIT）での冪等書き込みを心がけています。
- OpenAI API 呼び出しはフェイルセーフ（API障害やパース失敗時は例外を伝播させずフォールバック）かつリトライ（指数バックオフ）を組み込んでいます。
- テスト容易性のため、いくつかの内部 API 呼び出しは unittest.mock.patch で差し替え可能な設計になっています。

[0.1.0] - 2026-03-29
--------------------
Added
- パッケージ初期リリース。主要コンポーネントを追加。
  - kabusys パッケージ本体（__version__ = 0.1.0）。
  - サブパッケージの公開インターフェース: data, strategy, execution, monitoring。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（OS環境変数を保護して読み込み順: OS > .env.local > .env）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
  - .env パーサは以下をサポート:
    - コメント行と空行の無視、行頭の "export KEY=val" 形式のサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント処理（'#' の前が空白/タブの場合にコメントと判定）。
  - 重要な設定値をプロパティ化した Settings クラスを提供（J-Quants, kabu API, Slack, DBパス, 環境種別, ログレベル等）。
  - 環境変数の必須チェックを行う _require 関数。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）にバッチ（最大 20 銘柄）で問い合わせて銘柄別センチメント（-1.0〜1.0）を算出。
    - 1銘柄あたり記事数上限・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装し、トークン肥大化を回避。
    - JSON Mode を利用し、レスポンスの厳密なバリデーションを実施。JSON パース失敗時は前後の余分なテキストから最外の {} を抽出するフォールバックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。非リトライ系の失敗はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗時に既存データを保護する目的で、取得済みコードのみ DELETE → INSERT で差し替え（executemany を利用）。DuckDB 0.10 の executemany の空リスト制約に対応したガードあり。
    - テスト用フック: _call_openai_api を patch 可能。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロセンチメントは news_nlp.calc_news_window で決定される時間窓内のマクロキーワードにマッチする記事タイトルを抽出して LLM に評価させる。
    - API 障害やパース失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。リトライポリシー・ログ出力を実装。
    - 設定済み閾値（_BULL_THRESHOLD/_BEAR_THRESHOLD）、MA 係数やスケール、使用モデル (gpt-4o-mini) を定数化。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理用ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未セットの場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) を設定し無限ループを防止。
    - calendar_update_job: J-Quants からカレンダーを差分取得・バックフィルして保存（lookahead / backfill 対応、健全性チェックあり）。
    - DB 値優先・未登録日は曜日フォールバック等、DB がまばらな場合でも一貫した判断を行う実装。

  - pipeline (ETL)
    - ETLResult データクラスの追加（ETL 実行結果の構造化、品質問題とエラー集約、JSON 化ユーティリティ）。
    - 差分更新・バックフィル・品質チェックの設計を反映（_MIN_DATA_DATE, _DEFAULT_BACKFILL_DAYS 等）。
    - DuckDB の最大日付取得やテーブル存在チェック等のユーティリティを実装。

  - etl.py で ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を SQL ウィンドウ関数で一括計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - DuckDB 内で完結する設計、外部 API 呼び出しは行わない。

  - feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターン計算（複数ホライズンを1クエリで取得、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。必要な有効ペアが 3 未満の場合は None。
    - rank: 同順位は平均ランク扱い（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値除外）。

Changed
- （初期リリースのため特記すべき「変更」はなし）

Fixed
- （初期リリースのため過去バグ修正履歴はなし。ただし設計上の注意点や互換性配慮を実装）
  - .env 読み込みで OS 環境変数を保護する protected 集合を導入し、意図しない上書きを防止。
  - DuckDB の executemany の空パラメータ不許可に対応するガードを追加。
  - OpenAI レスポンスの JSON パース失敗に備え、レスポンス前後の余分なテキストから JSON オブジェクトを抽出して復元するフォールバックを追加。
  - DB 書き込みで例外発生時に ROLLBACK を試み、失敗時は警告ログを出力して上位へ例外を伝播。

Security
- 外部 API（OpenAI / J-Quants / kabu API / Slack）の API キーは環境変数経由で取得する設計。必須値は Settings でチェックするため、キー未設定時は ValueError を明示的に発生させる。

Notes / 実装上の設計注意
- ルックアヘッドバイアス回避: すべてのバッチ処理・スコア生成関数は target_date を引数に取り、内部で現在日時を参照しない実装になっています。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用。テスト時は _call_openai_api をモック可能。
- DuckDB を前提に実装（日付型や executemany の挙動に注意）。ai_scores / market_regime / prices_daily / raw_news / raw_financials 等のテーブルを参照/更新します。
- 環境変数自動ロードはプロジェクトルート検出（.git または pyproject.toml）を基準に行うため、配布後も CWD に依存しない挙動を狙っています。

今後の TODO（推測）
- strategy / execution / monitoring の具体実装（インポート先は __all__ に含まれているが実装がこの差分では未確認）。
- ai モデルやバッチサイズ、閾値等の運用パラメータ化（設定から変更可能にする）。
- ETL の品質チェック（quality モジュール）の詳細と自動アラート機構の実装。
- より詳細なログ/メトリクス出力（監視 / アラート統合）。

ライセンス / 著作権
- 本 CHANGELOG はコード内のドキュメント文字列・コメント・実装から推測して作成しています。実際のリリースノートとして利用する場合は、実装者の確認・補完を推奨します。