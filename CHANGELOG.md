CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
（詳細: https://keepachangelog.com/ja/1.0.0/）

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリースとして主要コンポーネントを追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。公開サブパッケージ: data, strategy, execution, monitoring を __all__ に含む（将来的なサブモジュール構成を示唆）。
  - 設定・環境変数管理:
    - src/kabusys/config.py を追加。
      - プロジェクトルート自動検出ロジック（.git または pyproject.toml 基準）を実装し、作業ディレクトリに依存しない .env 自動ロード機能を提供。
      - .env 読み込みは優先度: OS 環境変数 > .env.local (上書き) > .env（初期セット）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサは export KEY=val 形式、クォート内のエスケープ、行内コメントの扱いなどに対応。
      - 環境変数必須チェック用の _require、Settings クラスを提供。J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / ログレベル / 環境（development/paper_trading/live）等のプロパティを持つ。
      - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）や便利な is_live/is_paper/is_dev フラグを提供。
  - AI（自然言語処理）:
    - src/kabusys/ai/news_nlp.py を追加。
      - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄センチメント（-1.0〜1.0）を算出。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
      - バッチサイズ、1銘柄当たりの最大記事数/文字数制限、429・ネットワーク・5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーション（JSON復元、結果キー・型チェック、既知コードのみ採用、数値検査）を実装。
      - スコアの ±1.0 クリップ、DB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄データを保護）に対応。
      - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch による置換を想定）。
    - src/kabusys/ai/regime_detector.py を追加。
      - ETF 1321（日本225連動）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
      - prices_daily / raw_news を参照して ma200_ratio とマクロ記事のタイトル抽出を実行。OpenAI（gpt-4o-mini）へ送信して macro_sentiment を評価（記事がない場合は LLM 呼出しをスキップ）。
      - APIエラー・パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時はROLLBACK）。
      - ルックアヘッドバイアス防止設計（datetime.today() を参照しない、クエリに date < target_date を使用）を採用。
  - 研究（Research）モジュール:
    - src/kabusys/research/factor_research.py を追加。
      - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供。
      - データ不足時の扱い（条件未満は None）、SQL ウィンドウ関数を利用した効率的な実装、結果は (date, code) 辞書リストで返却。
    - src/kabusys/research/feature_exploration.py を追加。
      - 将来リターン計算（horizons引数対応、デフォルト [1,5,21]）、IC（Spearman rank correlation）計算、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
      - Pandas 等に依存せず、標準ライブラリと DuckDB で完結する設計。
    - src/kabusys/research/__init__.py で主要 API をエクスポート（calc_momentum/calc_value/calc_volatility/zscore_normalize 等）。
  - データプラットフォーム（Data）:
    - src/kabusys/data/calendar_management.py を追加。
      - JPX カレンダー管理：market_calendar テーブル参照・更新、営業日判定（is_trading_day/is_sq_day）、前後営業日探索（next_trading_day/prev_trading_day）、期間内営業日取得（get_trading_days）、夜間バッチ更新 job（calendar_update_job）を実装。
      - DB 登録値を優先し未登録日は曜日ベースでフォールバックする一貫性のあるロジックを採用。最大探索日数制限で無限ループを防止し、バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py を追加。
      - ETL のための ETLResult データクラスを提供（取得件数・保存件数・品質問題リスト・エラーリスト等を含む）。
      - 差分更新、バックフィル、安全な保存（idempotent）、品質チェックの収集を想定した設計（呼び出し元が方針を判断できるようにする）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
    - DuckDB との互換性や実行時の挙動（executemany の空リスト回避など）に配慮した実装を行っている。
  - その他ユーティリティ:
    - src/kabusys/ai/__init__.py および src/kabusys/research/__init__.py 等で公開 API を整理。

Changed
- 初版のため「変更」は無し（新規追加のみ）。

Fixed
- 初版のため「修正」は無し。

Design / Implementation notes (主な設計方針)
- ルックアヘッドバイアス回避: ほとんどの処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は例外を上位へ不用意に伝播せず、スコアをデフォルト値へフォールバックしたり該当チャンクをスキップすることでパイプライン全体の停止を避ける。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT DO UPDATE を想定）で実装。
- テスト容易性: OpenAI 呼び出しは内部でラップしており、テスト時に差し替え可能。DuckDB 依存部分は接続注入により単体テストが可能。
- スケーラビリティ: ニュース NLP は銘柄をチャンク（デフォルト 20 件）で分割して API 呼び出しすることで処理量を制御。

Breaking Changes
- 初版のため該当なし。

Security
- 現バージョンでは機密情報（API キー等）は環境変数経由で設定することを想定。.env の自動読み込みは便利だが本番では KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

今後の予定（省略版）
- strategy / execution / monitoring の実装充実化（現在は名前空間のみ公開）。
- ai モデルやバッチパラメータの設定外部化、より高度な品質チェックの導入。
- CI テスト・ドキュメント整備。

注記
- 実装はソースコード内の docstring とコメントに基づき推測してまとめています。実行環境や外部 API のバージョン差異により挙動が変わる可能性があります。