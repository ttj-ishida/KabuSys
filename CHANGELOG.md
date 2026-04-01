CHANGELOG
=========

すべての変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース (バージョン 0.1.0)
  - 基本パッケージ情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
    - OS 環境変数は保護（上書き除外）される仕組み
  - .env パーサ実装（kabusys.config._parse_env_line）
    - export プレフィックスに対応
    - シングル/ダブルクォート内のエスケープを正しく処理
    - インラインコメントの扱い（クォート外かつ直前が空白/タブの場合をコメントと判定）
  - Settings クラスを提供（環境変数読み取り・型変換・バリデーション）
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境 (development/paper_trading/live) / ログレベルの取得
    - env と log_level は許容値チェックを実施し、不正値は ValueError を送出

- データ基盤ユーティリティ (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを基にした営業日判定 API 実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得時は曜日ベース（土日除外）でフォールバック
    - 夜間バッチ: calendar_update_job により J-Quants から差分取得して冪等保存
    - バックフィル、健全性チェック (将来日付の異常検出)、最大探索日数による無限ループ防止
  - ETL パイプライン (pipeline)
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）
    - 差分取得 / 保存（idempotent 保存） / 品質チェックの設計方針を反映
    - DuckDB に関する互換性考慮（executemany の空リスト制約への対応等）

- 研究 (research)
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離を計算
    - ボラティリティ / 流動性 (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - バリュー (calc_value): raw_financials を用いた PER、ROE を計算（EPS 不在やゼロは None）
    - DuckDB を利用した SQL ベース実装、データ不足時の None 処理
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）対応、入力バリデーションあり
    - IC 計算 (calc_ic): スピアマン（ランク相関）でファクター有効性を評価、データ不足時は None
    - ランク変換ユーティリティ (rank): 同順位を平均ランクで扱う実装
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を標準ライブラリのみで計算

- AI / NLP (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news + news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini + JSON Mode）へバッチ評価
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB 比較）
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり記事数と文字数の上限でトリム
    - 再試行ポリシー: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ
    - レスポンス検証: JSON 抽出、results リスト検証、未知コード無視、スコア数値化・±1 にクリップ
    - 部分成功を考慮した冪等的な DB 書き換え（対象コードのみ DELETE→INSERT）
    - API キーは引数経由または環境変数 OPENAI_API_KEY を必須で参照。未設定だと ValueError
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して daily レジーム判定
    - マクロセンチメントはマクロキーワードでフィルタした記事タイトルを LLM で評価（JSON 出力期待）
    - LLM 呼び出しは専用実装でニュースモジュールと分離、API エラー時は macro_sentiment=0.0 のフェイルセーフ
    - 冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）

Changed
- 設計方針（全域）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計を徹底（target_date を明示的受け渡し）
  - OpenAI 呼び出し結果は厳密な JSON を期待するが、混入テキストがあっても最外側の {} を抽出して復元する耐性を追加
  - 全体的にフェイルセーフ設計:
    - 外部 API 失敗時は例外で停止させず安全側のデフォルト値（例: 0.0、スキップ）で継続する箇所を明確化
    - DB 書き込みは可能な限り部分失敗でも既存データを保護する方針

Fixed
- DuckDB 互換性対応
  - executemany に空リストを渡せないバージョンに配慮し、空リストの場合は実行をスキップするガードを追加

Notes / Known limitations
- OpenAI API の利用には OPENAI_API_KEY（または各関数の api_key 引数）が必須。未設定時は ValueError を送出する設計。
- raw_news.datetime は UTC で保存されている前提でウィンドウ計算を行う実装。タイムゾーン混在に注意。
- 一部モジュール（例: monitoring, strategy, execution）はパッケージ API に含まれるが、ここに記載されているのは現時点で実装が確認できたモジュール群（data, ai, research 等）。
- DuckDB から戻る日付型は date または ISO 文字列の両方を考慮して変換するユーティリティを実装しているが、環境による型の違いに注意。

クレジット
- 初期実装: コードベースに記載されたモジュール群と設計方針に基づき作成

--- 

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリース履歴に合わせて適宜編集してください。）