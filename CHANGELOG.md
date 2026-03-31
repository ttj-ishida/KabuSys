Changelog
=========
すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはプロジェクトのリリース履歴を分かりやすく追跡するためのものです。

v0.1.0 - 2026-03-31
-------------------

Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - __version__ を "0.1.0" として公開。パッケージの主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定 / ロード機能（kabusys.config）
  - Settings クラスを追加し、環境変数から各種設定を取得するプロパティ群を提供。
    - J-Quants / kabuAPI / Slack / データベースパス / 監視閾値 / システム環境（env/log_level 判定）などをサポート。
    - env（KABUSYS_ENV）と log_level（LOG_LEVEL）の値検証を実装。無効な値は ValueError を送出。
    - is_live / is_paper / is_dev といった環境判定ユーティリティを追加。
  - .env 自動読み込み機能を実装
    - プロジェクトルートの判定は __file__ を起点に .git または pyproject.toml を探索（CWDに依存しない）。
    - 読み込み順: OS環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサは以下をサポート/保護:
    - 空行 / コメント（#）スキップ
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなしの行のインラインコメント扱い（直前が空白/タブの場合のみ）

- AI モジュール（kabusys.ai）
  - ニュース NLU / NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None) を公開:
      - raw_news と news_symbols から指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）分のニュースを銘柄別に集約。
      - 1銘柄あたり最大記事数・最大文字数でトリム。
      - 最大 _BATCH_SIZE（デフォルト20）銘柄ごとに gpt-4o-mini（JSON mode）へバッチ送信。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時は対象コードのみ更新する安全な DB 書き込み（DELETE → INSERT）を実装。
      - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。その他はスキップして継続（フォールセーフ）。
      - 返り値: 書き込んだ銘柄数。
    - calc_news_window(target_date) を公開（UTC naive datetime を返す）：タイムウィンドウ計算ロジックを提供。
    - テスト用に内部の OpenAI 呼び出しポイント（_call_openai_api）をパッチ可能に設計。
    - DuckDB executemany の空リスト制約に配慮した実装（空パラメータは実行しない）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None) を公開:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime に保存。
      - ma200_ratio は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
      - マクロ記事が存在する場合のみ OpenAI を呼び出し（最大 _MAX_MACRO_ARTICLES 件）、失敗時は macro_sentiment=0.0 で継続。
      - OpenAI 呼び出しに対するリトライ / エラーハンドリングを実装（RateLimit / Timeout / 5xx 等）。
      - レコード書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）および例外時の ROLLBACK 保護を行う。
      - 返り値: 成功時 1 を返す。
    - モデル: gpt-4o-mini（JSON output を期待）。システムプロンプトにより厳密な JSON 応答を想定。

- データ / ETL / カレンダー（kabusys.data）
  - calendar_management モジュールを実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルが存在しない・未登録日の場合は曜日（平日＝営業日）ベースでフォールバックする一貫した挙動。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) による安全策。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS) を実装:
      - J-Quants から差分取得して market_calendar を更新（バックフィルと健全性チェックを含む）。
      - 取得失敗・異常時は 0 を返す。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（target_date, fetched/saved counts, quality_issues, errors 等を保持）。
    - ETL の設計方針を反映: 差分更新、バックフィル、品質チェック（重大度を持つがフェイルファストしない）、id_token 注入でテスト容易性を確保。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - etl モジュールは pipeline.ETLResult を再エクスポート（kabusys.data.etl）。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。データ不足に配慮（None）。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または欠損時は None）。
    - 各関数は DuckDB SQL を主に使用し、(date, code) をキーにした dict リストを返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（営業日換算）で将来リターンを計算。horizons の妥当性チェックあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク相関）で IC を算出。有効レコードが 3 未満なら None。
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ（丸めで ties 検出漏れ防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計要約。

Changed
- （初期リリースのため履歴なし）

Fixed
- （初期リリースのため履歴なし）

Security
- （初期リリースのため履歴なし）

Notes / 注意点
- OpenAI API
  - API キーは関数引数で注入可能。None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する関数が多いので注意。
  - LLM 呼び出し失敗時はフェイルセーフとして中立スコア（0.0）やスキップを行う設計。運用上の通知や再試行は呼び出し側で検討してください。
- DuckDB に関する互換性
  - executemany に対して空リストを渡すとエラーになる（DuckDB 0.10 系）。そのため空パラメータはスキップする分岐を挟んでいます。
- 日付 / ルックアヘッド
  - 全ての処理は内部で date.today() / datetime.today() を直接使用しない設計（ルックアヘッドバイアス防止）。関数は target_date を明示的に受け取り、その前提で動作します。
- 自動 .env ロード
  - テストなどで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。

今後の予定（提案）
- strategy / execution / monitoring サブパッケージの具体的実装（現状は __all__ に名前のみ存在）。
- 単体テスト・統合テストの追加（OpenAI 呼び出しはモック化可能な設計だがテスト実装を推奨）。
- J-Quants / kabu API クライアントの実装とドキュメント整備。
- スコアリング結果の可視化・バッチ監視ジョブの追加。

--- 
この CHANGELOG はコード内の実装から推測して作成しています。リリース日や項目の粒度は実プロジェクトの運用方針に合わせて調整してください。