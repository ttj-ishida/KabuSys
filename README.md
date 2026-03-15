# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム向けの軽量な骨組み（フレームワーク）です。データ取得、シグナル生成（ストラテジー）、注文実行、モニタリングといった主要機能をモジュール単位で分離して提供し、独自のアルゴリズムや実行ロジックを実装しやすくしています。

---

## 機能一覧

- データ管理（data）  
  市場データの取得・整形・キャッシュなどの責務を想定したモジュール。
- ストラテジー（strategy）  
  価格データや指標に基づいて売買シグナルを生成するためのロジックを実装するためのモジュール。
- 注文実行（execution）  
  ブローカーAPI（kabuステーション等）と接続して実際に発注・約定管理を行うためのモジュールを想定。
- モニタリング（monitoring）  
  ログ出力、アラート、ダッシュボードなど運用時の監視・通知を担うモジュールを想定。

> 現在のリポジトリはフレームワークの骨組み（パッケージ構造）を提供する状態です。各モジュール内に実装を追加してご利用ください。

---

## 必要条件 / 前提

- Python 3.8 以上を推奨
- ブローカーAPI（例：kabuステーション）の利用や外部ライブラリを使う場合は、各種APIキーやトークンが必要になります（本リポジトリはサンプル構成のため、認証の実装は含まれていません）。

---

## セットアップ手順

1. リポジトリをクローンする

   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化する（任意だが推奨）

   macOS / Linux:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. パッケージを開発モードでインストールする

   ```
   pip install -e .
   ```

4. 依存関係がある場合は `requirements.txt` を用意している想定です（本テンプレートでは未定義）。必要なライブラリをインストールしてください。

---

## 使い方（基本例）

このパッケージはモジュール単位で実装を拡張していくことを想定しています。簡単な使い方の例（擬似コード）を示します。

- サンプル構成イメージ

  - data モジュール: データ取得クラスを実装
  - strategy モジュール: シグナル生成クラスを実装
  - execution モジュール: 注文発注クラスを実装
  - monitoring モジュール: ログ・通知を実装

例: 簡単なドライバースクリプト（pseudo.py）

```python
from kabusys.data import DataClient  # ユーザ実装
from kabusys.strategy import MyStrategy  # ユーザ実装
from kabusys.execution import Executor  # ユーザ実装
from kabusys.monitoring import Monitor  # ユーザ実装

def main():
    data_client = DataClient(api_key="xxx")
    strategy = MyStrategy(params={})
    executor = Executor(api_credentials={})
    monitor = Monitor()

    # ループ例（実運用では適切なスケジューリングを行う）
    market_data = data_client.get_latest("7203.T")  # 銘柄コード例
    signal = strategy.generate(market_data)

    if signal == "BUY":
        executor.place_order(symbol="7203.T", side="BUY", size=100)
        monitor.notify("BUY placed for 7203.T")
    elif signal == "SELL":
        executor.place_order(symbol="7203.T", side="SELL", size=100)
        monitor.notify("SELL placed for 7203.T")

if __name__ == "__main__":
    main()
```

実際の実装は、APIの仕様（kabuステーション等）やリスク管理ポリシーに従って実装してください。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（現状）:

- src/
  - kabusys/
    - __init__.py         # パッケージ定義（__version__ = "0.1.0"）
    - data/
      - __init__.py       # データ関連モジュール（拡張用）
    - strategy/
      - __init__.py       # ストラテジーモジュール（拡張用）
    - execution/
      - __init__.py       # 注文実行モジュール（拡張用）
    - monitoring/
      - __init__.py       # モニタリングモジュール（拡張用）

README.md やライセンスファイル、セットアップ用のファイル（setup.cfg / pyproject.toml / requirements.txt 等）はリポジトリルートに配置することを推奨します。

---

## 開発ガイド（簡単な方針）

- 各責務を分離する
  - data: APIクライアント、データ整形、キャッシュ
  - strategy: 指標計算、シグナル判定（ステートレスにするのが望ましい）
  - execution: 注文の送信、約定確認、リトライ・エラーハンドリング
  - monitoring: ロギング、アラート（メール/Slack等）、状態可視化

- 設定・機密情報は環境変数や設定ファイルで管理し、ソースコードに直書きしない

- 単体テストを作成し、CIで自動実行する（pytest 等）

---

## テスト

現状はテストは含まれていません。テストを追加する場合は、ルートに `tests/` ディレクトリを作成し pytest を用いてテストケースを追加してください。

例:
```
pip install pytest
pytest
```

---

## 貢献

1. Issue を作成して問題点や提案を共有してください
2. フォークして、feature ブランチを作成し、プルリクエストを送ってください
3. コードは可読性を意識し、ユニットテスト、ドキュメントを添えてください

---

## ライセンス

プロジェクトのライセンスは指定されていません。使用・配布する場合は、適切なライセンス（例: MIT、Apache-2.0 など）をルートに追加してください。

---

その他質問や、実際のブローカー接続・サンプル実装（例: kabuステーション API を使った DataClient/Executor）について要望があれば、具体的な要件を教えてください。サンプル実装やテンプレートを作成します。