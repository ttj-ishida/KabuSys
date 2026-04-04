# Changelog

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従っています。
このファイルは人間に読みやすく、かつ機械で追跡しやすい形式で記述しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Breaking Changes, Security）に分類しています。
- 日付はリリース日（YYYY-MM-DD）を使用しています。
- 記載内容はソースコードの実装から推測してまとめたものであり、実際の運用や将来の変更により差異が生じる可能性があります。

Unreleased
- （今後の変更をここに記載）

[0.1.0] - 2026-04-04
Added
- パッケージ初期リリース。プロジェクトのコア機能群を提供。
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機能を実装。
      - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - export 形式、クォートされた値、インラインコメント、エスケープシーケンス等に対応する堅牢なパーサを実装。
      - 一部の環境変数（OS側の設定）を保護するための上書き制御（override/protected）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベース / 監視設定 / システム設定を取得するプロパティを定義。
      - env や LOG_LEVEL の値検証（許容値チェック）を実装。
      - パス系設定は Path に変換して expanduser に対応。
      - is_live / is_paper / is_dev 等のユーティリティプロパティを提供。
      - 必須環境変数未設定時には ValueError を送出する _require を用意。

  - kabusys.ai
    - news_nlp モジュール
      - raw_news / news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を算出して ai_scores テーブルへ書き込み。
      - JST ベースのニュース窓（前日 15:00 ～ 当日 08:30 を UTC に変換）を厳密に計算し、ルックアヘッドバイアスを排除。
      - 1銘柄あたりの記事数・文字数の上限（トリム）を実装し、バッチ(_BATCH_SIZE=20)で API 呼び出し。
      - JSON Mode を利用し、レスポンスのバリデーション（構造・型・既知コード・数値チェック）と ±1.0 のクリッピングを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx の場合は指数バックオフでリトライ。失敗時は当該チャンクをスキップして他チャンクの処理を継続するフェイルセーフ設計。
      - テスト容易性のため OpenAI API 呼び出し部分を差し替え可能（_call_openai_api を patch してモック可能）。
      - 書き込みは部分失敗に耐える設計（対象コードのみ DELETE → INSERT を行うことで他コードの既存データを保護）。
    - regime_detector モジュール
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
      - prices_daily からの取得は target_date 未満のデータのみを使用しルックアヘッドを防止。
      - マクロニュース抽出はキーワードベースで最大件数制限、LLM 呼び出しはリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
      - OpenAI クライアントを注入または環境変数 OPENAI_API_KEY を利用して初期化。
      - API 呼び出しや解析失敗時も例外を投げずに継続する戦略（フェイルセーフ）。ただし API キー未設定時は ValueError。

  - kabusys.research
    - factor_research
      - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、平均売買代金、出来高比率、PER/ROE（raw_financials ベース）などの定量ファクター計算を実装。
      - DuckDB 上で SQL とウィンドウ関数を用いて高性能に計算。
      - データ不足時の扱い（必要な行数に満たない場合は None）やログ出力を適切に実装。
    - feature_exploration
      - 将来リターン計算（horizons 指定可、デフォルト [1,5,21]）、IC（Spearman の順位相関）計算、ランク関数（同順位は平均ランク）、およびファクター統計サマリー（count/mean/std/min/max/median）を提供。
      - 入力検証（horizons 範囲チェック、欠損値除外等）を行う。
      - pandas 等の外部依存を使わず標準ライブラリのみで集計処理を実装。

  - kabusys.data
    - calendar_management
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
      - DB 登録値がある場合は DB を優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - calendar_update_job を実装して J-Quants API から差分取得 → 冪等保存（バックフィル・健全性チェック含む）。
      - 最大探索日数を設定して無限ループを防止。
    - pipeline / etl
      - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧などを保持、to_dict を提供）。
      - ETL の差分取得・保存・品質チェックの方針に基づく設計（backfill、品質チェックは収集して呼び出し元で評価）。
      - DuckDB のテーブル存在確認や最大日付取得ユーティリティを実装。
    - etl を含むデータパイプラインは jquants_client / quality モジュールと連携して動作する想定（実装は参照）。

  - 基盤
    - パッケージのエントリ __init__ を定義（__version__ = "0.1.0"、主要サブパッケージを __all__ で公開）。
    - DuckDB をデフォルトの分析 DB として利用する設計を中心に据えていることを明記。
    - テストしやすい設計（API 呼び出しの差替え、api_key の引数注入など）を意図的に導入。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Security
- 環境変数（API キー等）を明示的に必須チェックする実装を行い、誤設定時に早期に検出できるようにしている。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 環境向け）。

Notes / 設計上の重要ポイント（実装からの注意点）
- ルックアヘッドバイアス対策: 各モジュール（news_nlp/regime_detector/research）の設計で日時参照を外部から与える（target_date）形にし、内部で date.today()/datetime.today() を直接参照しないようにしている。
- API フェイルセーフ: OpenAI など外部 API の呼び出しはリトライとフォールバックを備え、失敗してもプロセス全体を停止させないように設計されている（ただし API キー未設定は例外）。
- DuckDB 互換性: executemany の空リストバインド等の実装上の制約に対する回避コードを含む（互換性確保のための注意）。
- ロギング: 各処理は適切な情報レベルのログを出力（info/debug/warning/exception）するようになっている。

今後の予定（想定）
- 監視 / 実行（execution / monitoring）モジュールの詳細実装および運用用 CLI の追加。
- J-Quants / kabu ステーションとの実運用接続のテスト、及び運用ドキュメントの整備。
- その他ファクター拡張・バックテスト / モデル学習パイプラインとの連携。

--- 
（注）本 CHANGELOG は提供されたソースコードの実装内容から推測して作成しています。実際の運用ルールや追加のサブモジュール、外部依存の状態により差異が生じる場合があります。必要であれば、リリース日・詳細・追加項目の追記・修正を行います。