# KabuSys

KabuSys は日本株の自動売買システムの骨組み（スケルトン）です。市場データ取得、売買戦略、注文実行、監視（ログ／アラート）といった主要コンポーネントをモジュール単位で分離しており、独自のロジックを実装して拡張できるよう設計されています。

バージョン: 0.1.0

---

## 機能一覧（想定・責務）

このリポジトリは基本的なパッケージ構成のみを含み、各モジュールに実装を追加することで機能するようになっています。各モジュールの想定責務は以下の通りです。

- data
  - 市場データの取得（REST / WebSocket）
  - データの整形・キャッシュ・永続化
- strategy
  - 売買ロジック（シグナル生成）
  - バックテスト用インターフェース
- execution
  - 注文の送信（証券会社APIとの連携：例：kabuステーション／kabu API 等）
  - 注文管理（注文の状態追跡、約定確認等）
- monitoring
  - ログ収集・出力（ファイル、外部ログサービス）
  - アラート（メール／Slack／LINE など）
  - 可視化・ダッシュボード連携

> 注意: 現在のコードベースはモジュールの雛形のみを含みます。実際の取引に利用する場合は、各モジュールに安全性・例外処理・テストを十分実装してください。

---

## セットアップ手順

1. リポジトリをクローンします。

   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. Python 仮想環境を作成・有効化します（Python 3.8+ を推奨）。

   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 開発用にパッケージを編集可能モードでインストールします。

   ```
   pip install -e .
   ```

   （依存パッケージがある場合は `requirements.txt` を用意して `pip install -r requirements.txt` を実行してください。一般的に使うライブラリ例: requests, websockets, pandas, numpy, python-dotenv など）

4. （任意）環境変数や認証情報を管理します。
   - 実際の証券会社APIを使う場合、APIキーや証明書を環境変数 / `.env` ファイル等に保存し、コード中で安全に読み込みます。
   - 例: `.env` に `KABU_API_TOKEN=xxxx` を保存し、`python-dotenv` で読み込む等。

---

## 使い方（基本例）

パッケージがインストールされると、以下のようにモジュールを参照できます。

- バージョン確認

```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- モジュールのインポート例（各モジュールに実装を追加して利用）

```python
from kabusys import data, strategy, execution, monitoring

# 例: データ取得クラスを実装している想定
# market_data = data.MarketDataClient(...)
# strategy = strategy.MyStrategy(...)
# executor = execution.OrderExecutor(...)
# monitor = monitoring.Monitor(...)

# サンプルフロー（擬似コード）
# prices = market_data.get_latest("7203")  # 銘柄コード
# signal = strategy.evaluate(prices)
# if signal == "BUY":
#     executor.send_order(symbol="7203", side="BUY", qty=100)
# monitor.record_event(...)
```

各モジュールにはクラスや関数を実装して、上記のように組み合わせて利用してください。

---

## ディレクトリ構成

現在の主要ファイル構成は以下の通りです。

```
src/
└── kabusys/
    ├── __init__.py            # パッケージのメタ情報 (バージョン等)
    ├── data/
    │   └── __init__.py        # 市場データ関連モジュール
    ├── strategy/
    │   └── __init__.py        # 戦略ロジック関連モジュール
    ├── execution/
    │   └── __init__.py        # 注文実行関連モジュール
    └── monitoring/
        └── __init__.py        # 監視・ログ関連モジュール
```

ファイルの抜粋:

- src/kabusys/__init__.py
  - パッケージ名：kabusys
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 開発ガイドライン（推奨）

- 各サブパッケージ（data, strategy, execution, monitoring）に責務ごとのクラス／関数を実装してください。
- 安全第一：注文処理には厳格な例外処理、再試行、ログ記録を実装してください。
- テストを書く：ユニットテスト、統合テストを用意して手動取引を防ぎます。
- 設定管理：APIキーや秘密情報はコードにハードコーディングしないでください。環境変数か秘密管理ツールを使ってください。
- バージョニング：変更を加えたら `src/kabusys/__init__.py` の __version__ を更新してください（Semantic Versioning 推奨）。

---

## 例：拡張のヒント

- data/
  - MarketDataClient（REST / WebSocket の実装）
  - DataStore（ローカルDBやファイルへの保存インターフェース）
- strategy/
  - BaseStrategy（evaluate() を提供する抽象クラス）
  - SampleStrategy（移動平均クロス等の具体実装）
- execution/
  - OrderExecutor（実注文送信・キャンセル・注文状態取得）
  - MockExecutor（テスト用に実際の注文を送らないモック）
- monitoring/
  - Logger（ファイル・標準出力）
  - Notifier（Slack/メール通報インターフェース）

---

## 貢献・ライセンス

- 貢献歓迎します。Pull Request / Issue を送ってください。
- ライセンスファイルは含まれていません。適切なライセンス (例: MIT) を追加してください。

---

以上。必要であれば README に記載する具体的な使用例（各クラスのサンプル実装）、推奨依存パッケージ、CI 設定例なども作成しますので教えてください。