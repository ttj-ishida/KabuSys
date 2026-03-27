CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のリポジトリ状態は v0.1.0 の初期リリースとして記録されています。以後の変更はここに追加してください。）

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初期リリース: kabusys バージョン 0.1.0 を追加。
  - パッケージ名/エントリ: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境/設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数から設定をロードする自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を上位ディレクトリから探索して自動検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 解析の強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、コメント処理の挙動を細かく処理。
  - Settings クラスを提供（settings インスタンスでアクセス可能）:
    - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティを用意。
    - env 値のバリデーション（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の許容値）と便宜的ユーティリティ（is_live / is_paper / is_dev）。
    - 必須値未設定時は ValueError を送出する _require 実装。

- AI ニュース/NLP (src/kabusys/ai/news_nlp.py)
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
  - 記事集約とトリムロジック（銘柄ごとに最大記事数 / 文字数制限）を実装。
  - バッチ処理（最大 20 銘柄/API 呼び出し）・JSON Mode を利用した堅牢なレスポンス検証 _validate_and_extract を実装。
  - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装、失敗はフェイルセーフでスキップ（例外を上げない）。
  - スコアは ±1.0 にクリップし、取得済みの銘柄のみ ai_scores を置換する（部分失敗時に他データを保護）。

- AI レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を追加。
  - マクロニュース抽出（マクロキーワード群）と OpenAI 呼び出しを組み合わせ、レスポンスパース失敗や API 障害時は macro_sentiment=0.0 へフォールバック。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 内部での OpenAI 呼び出しはテスト可能なように差し替え可能（モジュールローカル関数として設計）。

- データ ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を表現。
  - ETLResult.to_dict により品質問題を分かりやすく辞書化可能。
  - _get_max_date/_table_exists 等のヘルパーを提供。

- マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）とカレンダーを参照する営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時の曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索日数やバックフィル日数、健全性チェックの実装。
  - J-Quants クライアント経由で差分取得・保存（jquants_client.fetch_market_calendar / save_market_calendar を利用）。

- リサーチ（ファクター計算 / 特徴量探索） (src/kabusys/research/)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の None 処理）。
    - calc_volatility: 20 日 ATR / ATR 比率 / 20 日平均売買代金 / 出来高比率を計算。
    - calc_value: per / roe を raw_financials と prices_daily から計算。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズンの将来リターン計算（horizons バリデーションあり）。
    - calc_ic: Spearman ランク相関（IC）を計算するユーティリティ。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - 研究用 API を上位パッケージからエクスポート（kabusys.research.*）。

- その他
  - OpenAI クライアントの呼び出しは一箇所に集約し、テスト時に patch で差し替えられる設計（news_nlp._call_openai_api, regime_detector._call_openai_api）。
  - DuckDB との互換性を考慮した executemany の扱い（空リストバインド回避）。
  - 各モジュールで「ルックアヘッドバイアス防止」の設計方針を明示（date.today() / datetime.today() を内部参照しない、target_date を必須引数とする）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー等の秘密情報は環境変数経由で取り扱うことを推奨。Settings は未設定時に例外を投げるため、CI/運用環境での適切な管理が必要。
- .env ファイルの取り扱いに注意（リポジトリにコミットしないこと）。

Notes / 実装上の注意
- 自動環境読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御可能。
- OpenAI API 呼び出しは gpt-4o-mini と JSON mode を前提に設計。レスポンスの不正や API 障害時は安全側（スコア 0.0 やスキップ）で継続するため、外部依存で ETL 全体が停止しにくい構成。
- DuckDB のバージョン差異（配列バインドや executemany の空リスト挙動など）を考慮した実装箇所あり。
- 多くの処理で「欠損データ時は None またはスキップ」によって壊れにくくしているが、品質チェックモジュール（data.quality）と組み合わせて運用時の検知・対応を推奨。

お問い合わせ / 開発メモ
- 単体テスト実装時に OpenAI への依存を切り離すため、モジュール内の _call_openai_api を unittest.mock.patch 等で差し替えてテスト可能。
- ETLResult や Settings などは監査ログや運用ダッシュボード用に to_dict を利用して可視化することを想定。

--- 

（以降のリリースでは Unreleased セクションに変更点を記載し、ここに新バージョンを追記してください。）