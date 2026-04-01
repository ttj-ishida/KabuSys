# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。以下の主要機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。主要サブパッケージを __all__ で宣言（data, strategy, execution, monitoring）。  

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を読み込む（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env の行パーサは `export KEY=val`、クォート内のエスケープ、インラインコメントなどに対応。
    - .env.local は .env の値を上書き（ただし OS 環境変数は保護）。
  - Settings クラスを導入し、アプリケーション設定をプロパティで提供。
    - J-Quants・kabuステーション・Slack・データベースパス・監視閾値・実行環境（development/paper_trading/live）・ログレベル等のプロパティを持つ。
    - 必須変数未設定時は明示的に ValueError を発生させるバリデーションを実装。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーを扱う market_calendar を前提に、営業日判定・前後営業日取得・期間内営業日取得・SQ日判定を実装。
    - DB にカレンダー情報がない場合は曜日（土日）ベースでフォールバックするロジックを提供。
    - calendar_update_job: J-Quants から差分取得して冪等に保存する夜間ジョブ。バックフィル・健全性チェック（将来日付の異常検出）を実装。
    - 探索範囲上限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
  - ETL / パイプライン（pipeline / etl）
    - ETLResult データクラスを公開。ETL 実行結果（取得数・保存数・品質問題・エラー）の構造化を提供。
    - pipeline モジュールの設計方針に従い、差分更新、保存（idempotent）、品質チェック連携を想定。

- AI / ニュース NLP（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - score_news(conn, target_date, api_key=None) を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
      - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
      - 銘柄をチャンク（デフォルト 20）で OpenAI（gpt-4o-mini）へ送信し、JSON Mode レスポンスをパースして ai_scores テーブルへ書き込み。
      - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。API 失敗時はそのチャンクをスキップして継続。
      - レスポンスバリデーションを実装（results 配列・code の存在・数値型スコア・未知コード無視）。スコアは ±1.0 にクリップ。
      - DuckDB に対する書き込みは部分的に置換（DELETE → INSERT）して部分失敗時の既存データ保護を実現。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（regime_detector）
    - score_regime(conn, target_date, api_key=None) を実装。
      - ETF 1321（日経225連動）について直近 200 日の終値から MA200 乖離を計算（_calc_ma200_ratio）。
      - raw_news からマクロ経済キーワードに一致する記事タイトルを抽出（_fetch_macro_news）。
      - OpenAI（gpt-4o-mini）でマクロセンチメントを評価（_score_macro）。API 失敗時は macro_sentiment=0.0 でフォールバック。
      - MA 成分（70%）とマクロ成分（30%）を合成して regime_score を算出し、閾値により bull/neutral/bear をラベリング。
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - LLM 呼び出しはニュース NLP と独立した実装にし、モジュール結合を防止。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - ボラティリティ: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - バリュー: raw_financials と価格を組み合わせて PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB 上で SQL / ウィンドウ関数を用いて効率的に算出。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - 将来リターンの一括取得（任意ホライズン）を SQL で実行。horizons のバリデーションを実装。
    - IC（Spearman の ρ）を実装し、欠損や ties に対応したランク計算を行う。
    - factor_summary で基本統計量（count, mean, std, min, max, median）を算出。
  - kabusys.research パッケージで主要関数を再エクスポート。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- OpenAI API 呼び出しは api_key を引数で注入可能。環境変数が未設定の場合は明示的にエラーを出す設計により誤設定を検知可能。

### Performance & Reliability
- 多くの外部 API 呼び出し箇所（OpenAI, J-Quants）でリトライ／指数バックオフを採用。
- DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、部分失敗時の既存データ保護ロジックを実装。
- DuckDB 側の executemany に関する制約（空リスト不可）を考慮した実装。

### Notes / Limitations
- 本リリースは DuckDB を前提とした実装（DuckDB 接続オブジェクトを各関数に渡す設計）。
- OpenAI のレスポンスは JSON Mode を期待しているため、外部 API の応答仕様変更に伴う影響あり。
- 一部モジュール（例: strategy, execution, monitoring）は __all__ に含まれるが、今回のコードスナップショットでは主要実装が提供されていません。今後追加予定。

---

Reference: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)