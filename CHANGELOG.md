CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」形式に従っています。

0.1.0 - 2026-04-02
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys
  - __version__ = "0.1.0" を公開

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - コメント処理（クォートなしでの # を条件付きでコメントと認識）
  - _load_env_file の override/protected オプションで OS 環境変数保護に対応
  - Settings クラスを公開 (settings): J-Quants / kabu API / Slack / DB パス等のプロパティを提供
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）
    - env / log_level の検証（許容値チェック）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news + news_symbols を集約し、銘柄ごとのテキストを OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信
    - バッチサイズ、記事数／文字数上限、安全なリトライ（429・ネットワーク断・タイムアウト・5xx）を実装
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ
    - DuckDB の executemany の仕様差に配慮して、空リスト時は実行をスキップ
    - テスト容易性のため _call_openai_api の差し替え（mock）を想定
    - 公開 API: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して
      日次で 'bull' / 'neutral' / 'bear' を判定
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）を呼び出して macro_sentiment を取得
    - API 呼び出しのリトライ＆バックオフ、フェイルセーフ（失敗時 macro_sentiment=0.0）
    - ルックアヘッドバイアス対策（date < target_date のデータのみ使用、datetime.today() を参照しない）
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得・保存・品質チェックの骨格実装
    - ETLResult データクラスを提供（取得数、保存数、品質問題、エラー一覧などを含む）
    - DuckDB テーブル存在チェック等のユーティリティを含む
  - ETL の公開インターフェースを再エクスポート (kabusys.data.etl: ETLResult)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルに基づく営業日判定: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - カレンダー未取得時の曜日ベースフォールバック（土日は非営業日）
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=...)
      - J-Quants から差分取得、バックフィル、健全性チェック、冪等保存を実装
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止

  - jquants_client との連携を想定した設計（fetch/save 関数を呼び出す）

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム: calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日未満は None を返す）
    - ボラティリティ・流動性: calc_volatility(conn, target_date)
      - 20 日 ATR、ATR 比、20 日平均売買代金、出来高比率 等を計算（データ不足時は None）
    - バリュー: calc_value(conn, target_date)
      - raw_financials から最新財務データを取得し PER / ROE を計算
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=[...])
      - 一括 SQL で複数ホライズンの fwd return を取得
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関を実装（データ不足時は None）
    - ランク変換: rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
  - 研究用に外部ライブラリに依存せず、DuckDB / 標準ライブラリのみで実装

- テスト / デバッグ向け配慮
  - OpenAI 呼び出し箇所に差し替えポイントを用意（unittest.mock.patch で置換可能）
  - ロギングを多用し処理状況とフォールバックを可視化

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 特記事項なし

Notes / 実装上の設計方針ハイライト
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算はいずれも datetime.today()/date.today() を直接参照せず、
    呼び出し側から target_date を与える設計。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等への書き込みは DELETE → INSERT の形で既存データを上書きし、部分失敗時に他データを保護。
- OpenAI 呼び出しの堅牢性:
  - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフ・リトライ、
    パースエラーや非致命的失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB のバージョン差に配慮した実装。

今後の予定（例）
- strategy / execution / monitoring モジュールの公開インターフェース拡充
- テストカバレッジ拡張（特に OpenAI まわりのエラー処理）
- J-Quants / kabu API クライアント実装の安定化と認証フローの追加

---- 

（補注）上記はソースコードから推測して記載した CHANGELOG です。実際のリリースノート作成時は実装履歴やコミットログ、関連ドキュメントを参照の上、差分を確定してください。